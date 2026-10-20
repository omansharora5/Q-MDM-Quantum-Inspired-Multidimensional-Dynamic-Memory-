# Synthetic retrieval experiment

Re-run from the repository root with `.venv\Scripts\python -m benchmarks.run`.

Run: 2026-10-18T22:13:10.076257+00:00

Dataset SHA-256: `bd4ca310826eb23d7ffd9e25bea5080d2f20e11442061f9075d7b12091904cfa`

The fixture generator fixes questions and labels before execution. Three domains contain changed decisions, immutable source episodes, a low-overlap linked reason, a workflow and unrelated distractors. Abstention includes unknown vocabulary and a known project with an absent secret. Separate seeds alter distractors; this is not a learned-model train/test split. Corpus scale counts current records, with an additional historical decision version. Baseline methods rank the whole eligible corpus for their own top-eight seeds; graph methods expand their anchors up to 40 visited records. These candidate limits are production policy and apply in this experiment.

Recall@k counts relevant IDs at their expected versions. Precision divides those hits by returned top-k handles, including zero for empty answerable results. Coverage requires every required evidence ID. These three metrics exclude unanswerable questions, which have a separate abstention-success metric. Missing/error samples remain recorded and error counts are shown; quality means use successful samples. All returned context characters count toward the shared budget, although only first-k handles are graded. p50/p95 use linear interpolation across measured sequential calls, including all categories.

- Synthetic fixed templates with seeded distractors; small regression study, not a public benchmark or vendor comparison.
- Queries and relevance labels were fixed before the final measured run; no weights were tuned from these outputs.
- Pure in-process retrieval including per-call lexical indexing. Excludes DB/network, ingestion, LLM generation and answer accuracy.
- Vector means TF-IDF cosine over lexical tokens. No neural semantic embeddings or external memory products ran.
- Recall/precision use the first k returned handles under one shared serialized character budget. Source bodies are not opened.
- Input snapshots are already authorized shared data; these experiments do not test authentication or tenant enforcement.
- Historical labels require the expected record version. Current states and historical snapshots use fixed fixture dates.
- Graph methods can see explicit synthetic links; this measures retrieval given correct links, not extraction quality.
- Abstention is only zero-result retrieval: unknown vocabulary or a known project with a missing fact. It does not measure answer-model refusal.
- Sequential local timing is machine-dependent. p95 is descriptive for this sample; cache and import warmup are excluded.
- QWAM is a classical NumPy simulation on bounded graphs, without a claimed speedup or retrieval advantage.

`results.json` contains raw rows plus aggregate, by_category, by_scale and by_dataset summaries. `results.csv` contains the same raw trials. Each metric has SVG and PNG charts with overall, category and scale panels.

## Measured results

2,592 trials, seeds [11, 29, 47], distractors per dataset [24, 96, 240], 2 repeats, k=3, budget=3200 characters.

| Method | Recall@k | Precision@k | Complete coverage | Missing-fact zero-result rate | p50 ms | p95 ms | Errors |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BM25 | 0.833 | 0.444 | 0.667 | 0.500 | 8.178 | 20.653 | 0 |
| TF-IDF cosine (lexical) | 0.833 | 0.444 | 0.667 | 0.500 | 8.064 | 20.267 | 0 |
| Bounded graph traversal | 1.000 | 0.500 | 1.000 | 0.500 | 8.827 | 22.180 | 0 |
| Personalized PageRank | 1.000 | 0.500 | 1.000 | 0.500 | 9.727 | 22.369 | 0 |
| PACE intent + evidence bundles | 1.000 | 0.500 | 1.000 | 0.500 | 9.608 | 22.966 | 0 |
| CTQW (experimental) | 1.000 | 0.500 | 1.000 | 0.500 | 9.475 | 22.985 | 0 |

The graph fixtures explicitly provide the low-overlap evidence link. Equal scores across graph methods do not establish an advantage for PACE or QWAM. Inspect the missing-fact zero-result rate and raw errors alongside successful retrieval. No answer model ran, so these are not answer correctness scores.
