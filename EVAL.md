# Evaluation Report

## Dataset

The evaluation used the 26-question golden dataset in `evals/golden_dataset.json`: 21 answerable questions and 5
unanswerable questions. It includes direct, reworded, and multi-part questions, with answerable items grounded to
the supplied university document.

## Method and configurations

Each configuration was evaluated with a fresh vector index. Both used `sentence-transformers/all-MiniLM-L6-v2`
and `top_k = 5`; the tested chunk settings were:

| Configuration | Chunk size | Chunk overlap |
|---|---:|---:|
| A_chunk500_overlap50 | 500 | 50 |
| B_chunk1000_overlap150 | 1000 | 150 |

Retrieval was measured against the dataset's source-page ground truth. LLM-dependent evaluation used the configured
answer-generation pipeline and an LLM judge. Requests are spaced by at least two seconds by default
(`LLM_MIN_REQUEST_INTERVAL_S` can override this); HTTP 429 retries use exponential backoff and honor `Retry-After`
when supplied.

## Results

### Retrieval metrics

| Metric | A_chunk500_overlap50 | B_chunk1000_overlap150 |
|---|---:|---:|
| hit_rate@k | 1.0 | 1.0 |
| recall@k | 1.0 | 1.0 |
| mrr | 0.7857 | 0.7143 |
| mean_top_score_answerable | 0.5748 | 0.5121 |
| mean_top_score_unanswerable | 0.486 | 0.4442 |

### LLM-dependent metrics

| Metric | A_chunk500_overlap50 | B_chunk1000_overlap150 |
|---|---:|---:|
| faithfulness | 1.0 | 1.0 |
| answer_correctness | 1.0 | 1.0 |
| context_relevance | 1.0 | 1.0 |
| citation_correctness | 0.8 | 0.5882 |
| correct_refusal_or_answer_rate | 0.9615 | 0.8462 |
| correct_refusal_on_unanswerable | 1 | 1 |
| judged_questions | 20 | 17 |

These are the values reported in `evals/results/latest.md`. Repeated HTTP 429 rate-limit responses prevented complete
LLM evaluation: only 20 questions for Configuration A and 17 for Configuration B were judged. The LLM-dependent
metrics are therefore **partial results, not complete 26-question results**. The judge uses the same model as the
answer generator, which may bias judge scores upward. The displayed values should be interpreted with these
limitations in mind.

## Selected configuration

Configuration A is selected by the evaluation's retrieval ranking rule (recall, then MRR). Both configurations
achieved recall@k of 1.0, while A had the higher MRR (0.7857 versus 0.7143). A also had higher mean top scores for
answerable and unanswerable questions, and its reported citation correctness and correct refusal-or-answer rate
were higher. The LLM-dependent comparison is provisional because those metrics are partial.

## Limitations and next steps

The HTTP 429 responses limited successful LLM requests. Although the client applies request spacing, exponential
backoff, and provider `Retry-After` delays, these results do not establish that the provider rate-limit issue is
resolved. A further evaluation with successful LLM requests is needed. Rerun both configurations and review the
per-question results before treating the LLM-dependent metrics or the configuration comparison as final.
