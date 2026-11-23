"""The evaluation maths must itself be tested."""
import json

from evals.run_eval import retrieval_metrics, save_results

REL = {("a.pdf", 2), ("a.pdf", 5)}


def test_hit_recall_mrr_when_first_result_is_relevant():
    m = retrieval_metrics([("a.pdf", 2), ("b.pdf", 1), ("a.pdf", 5)], REL)
    assert m == {"hit": 1.0, "recall": 1.0, "rr": 1.0}


def test_reciprocal_rank_when_relevant_result_is_third():
    m = retrieval_metrics([("b.pdf", 1), ("b.pdf", 2), ("a.pdf", 5)], REL)
    assert m["hit"] == 1.0 and m["recall"] == 0.5 and abs(m["rr"] - 1 / 3) < 1e-9


def test_miss():
    assert retrieval_metrics([("b.pdf", 1)], REL) == {"hit": 0.0, "recall": 0.0, "rr": 0.0}


def test_result_checkpoint_is_written_as_partial_then_complete(tmp_path):
    result = {"config": {"name": "small"}, "summary": {"recall@k": 0.5, "mrr": 0.25}}
    path = tmp_path / "eval.json"

    save_results(path, "stamp", 2, [result], complete=False)
    partial = json.loads(path.read_text(encoding="utf-8"))
    assert partial["status"] == "partial"
    assert partial["completed_configs"] == ["small"]
    assert partial["best_config"] is None

    save_results(path, "stamp", 2, [result], complete=True)
    complete = json.loads(path.read_text(encoding="utf-8"))
    assert complete["status"] == "complete"
    assert complete["best_config"] == "small"
