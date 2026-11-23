"""Reproducible evaluation. One command:

    python -m evals.run_eval                 # retrieval + answer metrics (needs LLM_API_KEY)
    python -m evals.run_eval --skip-llm      # retrieval metrics only

For every config in evals/configs.json it builds a FRESH index from data/corpus/, runs every question in
evals/golden_dataset.json and saves real results to evals/results/. Nothing is hard-coded.
"""
import argparse
import json
import re
import tempfile
from datetime import datetime
from pathlib import Path
from statistics import mean

from app.config import Settings
from app.errors import AppError
from app.services.container import build_services

ROOT = Path(__file__).resolve().parent
JUDGE_PROMPT = """You are a strict evaluator of a question-answering system.
Question: {question}
Reference answer: {reference}
Retrieved context:
{context}
System answer: {answer}

Score each from 1 (worst) to 5 (best):
- faithfulness: every claim in the system answer is supported by the retrieved context.
- correctness: the system answer agrees with the reference answer.
- context_relevance: the retrieved context is relevant to the question.
Reply with JSON only: {{"faithfulness": n, "correctness": n, "context_relevance": n}}"""


# ---------------- retrieval metrics (pure functions, unit tested) ----------------
def relevant_units(item: dict) -> set[tuple[str, int]]:
    return {(item["source_document"], p) for p in item.get("source_pages", [])}


def retrieval_metrics(ranked: list[tuple[str, int]], relevant: set[tuple[str, int]]) -> dict:
    """ranked = [(filename, page), ...] best first. Returns hit, recall and reciprocal rank."""
    found = relevant & set(ranked)
    rr = next((1 / i for i, unit in enumerate(ranked, 1) if unit in relevant), 0.0)
    return {"hit": 1.0 if found else 0.0, "recall": len(found) / len(relevant) if relevant else 0.0, "rr": rr}


def judge(llm, item, response) -> dict | None:
    context = "\n---\n".join(c.text for c in response.retrieved_chunks if c.used_in_context) or "(none)"
    reply = llm.chat([{"role": "user", "content": JUDGE_PROMPT.format(
        question=item["question"], reference=item["reference_answer"], context=context, answer=response.answer)}])
    match = re.search(r"\{.*?\}", reply, re.S)
    try:
        scores = json.loads(match.group(0))
        return {k: (float(scores[k]) - 1) / 4 for k in ("faithfulness", "correctness", "context_relevance")}
    except (AttributeError, ValueError, KeyError):
        return None


def run_config(cfg: dict, dataset: list[dict], corpus: list[Path], skip_llm: bool) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(chroma_dir=tmp, chunk_size=cfg["chunk_size"], chunk_overlap=cfg["chunk_overlap"],
                            top_k=cfg["top_k"], embedding_model=cfg["embedding_model"])
        services = build_services(settings)
        try:
            for path in corpus:
                services.ingestion.ingest(path.name, path.read_bytes())
            retriever, k = services.rag.retriever, cfg["top_k"]

            rows, judged_ok = [], 0
            for item in dataset:
                retrieved = retriever.retrieve(item["question"], k)
                row = {"id": item["id"], "answerable": item["answerable"],
                       "top_score": retrieved[0].score if retrieved else 0.0}
                if item["answerable"]:
                    row.update(retrieval_metrics([(c.filename, c.page) for c in retrieved], relevant_units(item)))
                if not skip_llm:
                    try:
                        resp = services.rag.ask(item["question"], k)
                        row["answered"] = resp.answerable
                        row["refusal_correct"] = resp.answerable == item["answerable"]
                        if item["answerable"] and resp.answerable:
                            rel = relevant_units(item)
                            by_id = {c.chunk_id: c for c in resp.retrieved_chunks}
                            row["citation_correct"] = float(any(
                                (by_id[c.chunk_id].filename, by_id[c.chunk_id].page) in rel for c in resp.citations))
                            scores = judge(services.rag.llm, item, resp)
                            if scores:
                                row.update(scores)
                                judged_ok += 1
                    except AppError as exc:
                        row["error"] = exc.code
                rows.append(row)
        finally:
            services.store.close()

    def avg(key, subset=None):
        vals = [r[key] for r in (subset or rows) if key in r]
        return round(mean(vals), 4) if vals else None

    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    summary = {"hit_rate@k": avg("hit"), "recall@k": avg("recall"), "mrr": avg("rr"),
               "mean_top_score_answerable": avg("top_score", answerable),
               "mean_top_score_unanswerable": avg("top_score", unanswerable)}
    if not skip_llm:
        summary.update({"faithfulness": avg("faithfulness"), "answer_correctness": avg("correctness"),
                        "context_relevance": avg("context_relevance"), "citation_correctness": avg("citation_correct"),
                        "correct_refusal_or_answer_rate": avg("refusal_correct"),
                        "correct_refusal_on_unanswerable": avg("refusal_correct", unanswerable),
                        "judged_questions": judged_ok})
    return {"config": cfg, "summary": summary, "per_question": rows}


def save_results(path: Path, stamp: str, dataset_size: int, results: list[dict], complete: bool) -> None:
    best = max(results, key=lambda r: (r["summary"]["recall@k"] or 0, r["summary"]["mrr"] or 0))
    payload = {
        "timestamp": stamp,
        "questions": dataset_size,
        "status": "complete" if complete else "partial",
        "completed_configs": [r["config"]["name"] for r in results],
        "best_config": best["config"]["name"] if complete else None,
        "results": results,
    }
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary_path.replace(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(ROOT / "golden_dataset.json"))
    ap.add_argument("--configs", default=str(ROOT / "configs.json"))
    ap.add_argument("--corpus", default="data/corpus")
    ap.add_argument("--skip-llm", action="store_true")
    args = ap.parse_args()

    if not Path(args.dataset).exists():
        raise SystemExit(f"Missing {args.dataset}. Copy evals/golden_dataset.template.json and fill it from YOUR documents.")
    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    corpus = sorted(p for p in Path(args.corpus).glob("*") if p.suffix.lower() in (".pdf", ".docx"))
    if not corpus:
        raise SystemExit(f"No PDF/DOCX files in {args.corpus}.")
    configs = json.loads(Path(args.configs).read_text(encoding="utf-8"))

    results = []
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    result_path = out / f"eval_{stamp}.json"
    for cfg in configs:
        print(f"Running config {cfg['name']} ...")
        results.append(run_config(cfg, dataset, corpus, args.skip_llm))
        save_results(result_path, stamp, len(dataset), results, complete=False)
        print(f"Checkpoint saved to {result_path}")

    best = max(results, key=lambda r: (r["summary"]["recall@k"] or 0, r["summary"]["mrr"] or 0))
    save_results(result_path, stamp, len(dataset), results, complete=True)

    metrics = list(results[0]["summary"])
    lines = ["| metric | " + " | ".join(r["config"]["name"] for r in results) + " |",
             "|---|" + "---|" * len(results)]
    lines += [f"| {m} | " + " | ".join(str(r["summary"][m]) for r in results) + " |" for m in metrics]
    table = "\n".join(lines)
    (out / "latest.md").write_text(f"Questions: {len(dataset)}  |  Best config: {best['config']['name']}\n\n{table}\n",
                                   encoding="utf-8")
    print("\n" + table + f"\n\nBest config (by recall, then MRR): {best['config']['name']}")
    print(f"Saved to {result_path} and {out / 'latest.md'}")


if __name__ == "__main__":
    main()
