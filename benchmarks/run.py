"""Run with python -m benchmarks.run. No server, database, credentials or LLM."""

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter_ns

from mnemograph.models import Recall
from mnemograph.retrieval import Pace

from .fixtures import CATEGORIES, SCALES, SEEDS, make_fixture

METHODS = ("bm25", "vector", "beam", "ppr", "pace", "qwam")
LABELS = {"bm25": "BM25", "vector": "TF-IDF cosine (lexical)", "beam": "Bounded graph traversal",
          "ppr": "Personalized PageRank", "pace": "PACE intent + evidence bundles", "qwam": "CTQW (experimental)"}
ROOT = Path(__file__).resolve().parents[1]
LIMITATIONS = [
    "Synthetic fixed templates with seeded distractors; small regression study, not a public benchmark or vendor comparison.",
    "Queries and relevance labels were fixed before the final measured run; no weights were tuned from these outputs.",
    "Pure in-process retrieval including per-call lexical indexing. Excludes DB/network, ingestion, LLM generation and answer accuracy.",
    "Vector means TF-IDF cosine over lexical tokens. No neural semantic embeddings or external memory products ran.",
    "Recall/precision use the first k returned handles under one shared serialized character budget. Source bodies are not opened.",
    "Input snapshots are already authorized shared data; these experiments do not test authentication or tenant enforcement.",
    "Historical labels require the expected record version. Current states and historical snapshots use fixed fixture dates.",
    "Graph methods can see explicit synthetic links; this measures retrieval given correct links, not extraction quality.",
    "Abstention is only zero-result retrieval: unknown vocabulary or a known project with a missing fact. It does not measure answer-model refusal.",
    "Sequential local timing is machine-dependent. p95 is descriptive for this sample; cache and import warmup are excluded.",
    "QWAM is a classical NumPy simulation on bounded graphs, without a claimed speedup or retrieval advantage.",
]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def write_results(path, result):
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def score(result, question, k):
    handles = result["handles"][:k]
    relevant = set(question["relevant_ids"])
    expected = question["expected_versions"]
    hits = {item["id"] for item in handles if item["id"] in relevant and item["version"] == expected.get(item["id"], item["version"])}
    return {"recall_at_k": len(hits)/len(relevant) if relevant else None,
            "evidence_precision": len(hits)/len(handles) if relevant and handles else 0. if relevant else None,
            "coverage": float(hits == relevant) if relevant else None,
            "abstention_success": float(not result["handles"]) if not relevant else None,
            "stale_version_errors": sum(item["id"] in expected and item["version"] != expected[item["id"]] for item in handles),
            "context_chars": result["context_chars"], "retrieved_ids": [item["id"] for item in handles],
            "returned_versions": {item["id"]: item["version"] for item in handles}, "hits": len(hits)}


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values)-1)*fraction
    lower = int(position)
    return values[lower] + (values[min(lower+1, len(values)-1)]-values[lower])*(position-lower)


def aggregate(rows, keys):
    groups = {}
    for row in rows:
        group = tuple(row[key] for key in keys)
        groups.setdefault(group, []).append(row)
    output = []
    for group, samples in groups.items():
        successful = [row for row in samples if not row.get("error")]
        item = dict(zip(keys, group))
        item.update({"samples": len(samples), "errors": len(samples)-len(successful)})
        for metric in ("recall_at_k", "evidence_precision", "coverage", "context_chars", "abstention_success"):
            values = [row[metric] for row in successful if row.get(metric) is not None]
            item[metric] = statistics.mean(values) if values else None
        timings = [row["latency_ms"] for row in successful]
        item.update({"p50_ms": percentile(timings, .5) if timings else None,
                     "p95_ms": percentile(timings, .95) if timings else None,
                     "stale_version_errors": sum(row["stale_version_errors"] for row in successful)})
        output.append(item)
    return output


def draw_plots(result, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    paths = []
    for metric, title in (("recall_at_k", "Evidence recall@k"), ("evidence_precision", "Evidence precision@k"),
                          ("coverage", "Complete evidence-set coverage@k"), ("abstention_success", "Zero-result rate on missing-fact queries"), ("context_chars", "Serialized context characters"),
                          ("p50_ms", "Median retrieval time (ms)"), ("p95_ms", "95th percentile retrieval time (ms)")):
        figure, axes = plt.subplots(1, 3, figsize=(16, 5), gridspec_kw={"width_ratios": [1, 1.4, 1.2]})
        overall = {row["method"]: row.get(metric) for row in result["aggregate"]}
        axes[0].barh(range(len(METHODS)), [overall.get(method) or 0 for method in METHODS], color="#2f716c")
        axes[0].set_yticks(range(len(METHODS)), [LABELS[method] for method in METHODS], fontsize=8)
        axes[0].set_title("All scenarios")
        matrix = np.full((len(METHODS), len(CATEGORIES)), np.nan)
        for row in result["by_category"]:
            if row.get(metric) is not None:
                matrix[METHODS.index(row["method"]), CATEGORIES.index(row["category"])] = row[metric]
        picture = axes[1].imshow(matrix, aspect="auto", cmap="YlGnBu", vmin=0,
                                  vmax=1 if metric in ("recall_at_k", "evidence_precision", "coverage", "abstention_success") else None)
        axes[1].set_xticks(range(len(CATEGORIES)), [name.replace("_", "\n") for name in CATEGORIES], fontsize=8)
        axes[1].set_yticks(range(len(METHODS)), METHODS, fontsize=8)
        axes[1].set_title("By question category; blank = N/A")
        figure.colorbar(picture, ax=axes[1], shrink=.7)
        for method in METHODS:
            points = sorted((row["memories_per_dataset"], row[metric]) for row in result["by_scale"]
                            if row["method"] == method and row.get(metric) is not None)
            axes[2].plot([p[0] for p in points], [p[1] for p in points], marker="o", label=method)
        axes[2].set_xlabel("Current memory records per dataset")
        axes[2].set_title("By corpus size")
        axes[2].legend(fontsize=7)
        if metric in ("recall_at_k", "evidence_precision", "coverage", "abstention_success"):
            axes[0].set_xlim(0, 1.05)
            axes[2].set_ylim(0, 1.05)
        for axis in axes:
            axis.spines[["top", "right"]].set_visible(False)
        figure.suptitle(title + " | synthetic retrieval study", fontsize=13)
        figure.text(.01, .01, f"k={result['config']['k']}, budget={result['config']['budget_chars']} chars; no LLM or database latency", fontsize=8)
        figure.tight_layout(rect=(0, .04, 1, .95))
        for extension in ("svg", "png"):
            name = f"{metric}.{extension}"
            figure.savefig(output/name, dpi=160)
            paths.append(name)
        plt.close(figure)
    return paths


def run(output, seeds=SEEDS, scales=SCALES, repeats=2, budget_chars=3200, k=3):
    if not seeds or not scales or repeats < 1 or k < 1 or min(scales) < 0:
        raise ValueError("Nonempty seeds/scales, positive repeats/k and nonnegative scale required")
    Recall(query="validate", budget_chars=budget_chars)
    retrieval_hash = hashlib.sha256((ROOT/"mnemograph/retrieval.py").read_bytes()).hexdigest()
    fixture_hash = hashlib.sha256(Path(__file__).with_name("fixtures.py").read_bytes()).hexdigest()
    datasets = [(seed, scale, *make_fixture(seed, scale)) for seed in seeds for scale in scales]
    dataset_hash = digest([{"seed": seed, "scale": scale, "state": state, "questions": questions}
                           for seed, scale, state, questions in datasets])
    retriever = Pace()
    warm_state, warm_questions = make_fixture(seeds[0], min(scales))
    for method in METHODS:
        retriever.retrieve(warm_state, Recall(query=warm_questions[0]["query"], dataset="personal", strategy=method, budget_chars=budget_chars))
    rows = []
    for seed, scale, state, questions in datasets:
        for repeat in range(repeats):
            for offset, question in enumerate(questions):
                for method in METHODS[(offset+repeat) % len(METHODS):]+METHODS[:(offset+repeat) % len(METHODS)]:
                    row = {"seed": seed, "distractors_per_dataset": scale, "memories_per_dataset": scale+5,
                           "repeat": repeat, "question_id": question["id"], "category": question["category"],
                           "dataset": question["dataset"], "method": method, "relevant_ids": question["relevant_ids"],
                           "query": question["query"], "as_of": question["as_of"], "error": None}
                    request = Recall(query=question["query"], dataset=question["dataset"], strategy=method,
                                     as_of=question["as_of"], budget_chars=budget_chars)
                    started = perf_counter_ns()
                    try:
                        packet = retriever.retrieve(state, request)
                        row["latency_ms"] = (perf_counter_ns()-started)/1_000_000
                        row.update(score(packet, question, k))
                        row.update({"visited": packet["visited"], "truncated": packet["truncated"]})
                        if packet["context_chars"] > budget_chars:
                            raise AssertionError("Retriever exceeded the shared context budget")
                    except Exception as exc:
                        row["latency_ms"] = (perf_counter_ns()-started)/1_000_000
                        row["error"] = f"{type(exc).__name__}: {exc}"
                    rows.append(row)
    if retrieval_hash != hashlib.sha256((ROOT/"mnemograph/retrieval.py").read_bytes()).hexdigest() or fixture_hash != hashlib.sha256(Path(__file__).with_name("fixtures.py").read_bytes()).hexdigest():
        raise RuntimeError("Retrieval or fixture source changed during the run; rerun against frozen files")
    versions = {name: importlib.metadata.version(name) for name in ("numpy", "matplotlib", "pydantic")}
    result = {"status": "completed_with_errors" if any(row["error"] for row in rows) else "completed",
              "run_at": datetime.now(timezone.utc).isoformat(), "dataset_hash": dataset_hash,
              "methods": list(METHODS), "method_labels": LABELS, "categories": list(CATEGORIES),
              "config": {"seeds": list(seeds), "distractor_scales": list(scales), "repeats": repeats, "k": k,
                         "budget_chars": budget_chars, "max_hops": 2, "warmup": "One untimed call per method"},
              "runtime": {"python": sys.version, "platform": platform.platform(), "packages": versions,
                          "retrieval_sha256": retrieval_hash, "fixtures_sha256": fixture_hash},
              "aggregate": aggregate(rows, ("method",)), "by_category": aggregate(rows, ("method", "category")),
              "by_scale": aggregate(rows, ("method", "memories_per_dataset")),
              "by_dataset": aggregate(rows, ("method", "dataset")), "limitations": LIMITATIONS, "raw": rows}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    result["plots"] = draw_plots(result, output)
    write_results(output/"results.json", result)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (output/"results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: json.dumps(value) if isinstance(value, (list, dict)) else value for key, value in row.items()} for row in rows)
    methodology = "# Synthetic retrieval experiment\n\nRe-run from the repository root with `.venv\\Scripts\\python -m benchmarks.run`.\n\n"
    methodology += f"Run: {result['run_at']}\n\nDataset SHA-256: `{dataset_hash}`\n\n"
    methodology += "The fixture generator fixes questions and labels before execution. Three domains contain changed decisions, immutable source episodes, a low-overlap linked reason, a workflow and unrelated distractors. Abstention includes unknown vocabulary and a known project with an absent secret. Separate seeds alter distractors; this is not a learned-model train/test split. Corpus scale counts current records, with an additional historical decision version. Baseline methods rank the whole eligible corpus for their own top-eight seeds; graph methods expand their anchors up to 40 visited records. These candidate limits are production policy and apply in this experiment.\n\n"
    methodology += "Recall@k counts relevant IDs at their expected versions. Precision divides those hits by returned top-k handles, including zero for empty answerable results. Coverage requires every required evidence ID. These three metrics exclude unanswerable questions, which have a separate abstention-success metric. Missing/error samples remain recorded and error counts are shown; quality means use successful samples. All returned context characters count toward the shared budget, although only first-k handles are graded. p50/p95 use linear interpolation across measured sequential calls, including all categories.\n\n"
    methodology += "\n".join(f"- {item}" for item in LIMITATIONS)
    methodology += "\n\n`results.json` contains raw rows plus aggregate, by_category, by_scale and by_dataset summaries. `results.csv` contains the same raw trials. Each metric has SVG and PNG charts with overall, category and scale panels.\n"
    methodology += f"\n## Measured results\n\n{len(rows):,} trials, seeds {list(seeds)}, distractors per dataset {list(scales)}, {repeats} repeats, k={k}, budget={budget_chars} characters.\n\n"
    methodology += "| Method | Recall@k | Precision@k | Complete coverage | Missing-fact zero-result rate | p50 ms | p95 ms | Errors |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n"
    for item in result["aggregate"]:
        values = [item[name] for name in ("recall_at_k", "evidence_precision", "coverage", "abstention_success", "p50_ms", "p95_ms")]
        cells = [f"{value:.3f}" if value is not None else "N/A" for value in values]
        methodology += "| " + " | ".join([LABELS[item["method"]], *cells, str(item["errors"])]) + " |\n"
    methodology += "\nThe graph fixtures explicitly provide the low-overlap evidence link. Equal scores across graph methods do not establish an advantage for PACE or QWAM. Inspect the missing-fact zero-result rate and raw errors alongside successful retrieval. No answer model ran, so these are not answer correctness scores.\n"
    (output/"README.md").write_text(methodology, encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"artifacts/benchmarks")
    arguments = parser.parse_args()
    result = run(arguments.output)
    print(json.dumps({"status": result["status"], "trials": len(result["raw"]), "dataset_hash": result["dataset_hash"],
                      "aggregate": result["aggregate"], "output": str(arguments.output)}, indent=2))


if __name__ == "__main__":
    main()
