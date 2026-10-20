from datetime import datetime

from benchmarks.fixtures import make_fixture
from benchmarks.run import METHODS, aggregate, digest, score, write_results
from mnemograph.models import Recall
from mnemograph.retrieval import Pace, memories_at, terms


def test_fixture_repeatability_and_historical_ground_truth():
    state, questions = make_fixture(11, 3)
    assert digest((state, questions)) == digest(make_fixture(11, 3))
    assert digest((state, questions)) != digest(make_fixture(29, 3))
    assert len(state["entities"]) == 24
    for question in questions:
        selected = memories_at(state, datetime.fromisoformat(question["as_of"]) if question["as_of"] else None,
                               dataset=question["dataset"])
        assert set(question["relevant_ids"]) <= selected.keys()
        for key, version in question["expected_versions"].items():
            assert selected[key]["version"] == version
        if question["category"] == "associative":
            support = state["entities"][question["relevant_ids"][1]]["payload"]
            assert not terms(question["query"]) & terms(support["title"]+" "+support["content"])


def test_metrics_penalize_partial_evidence_and_stale_versions():
    question = {"relevant_ids": ["a", "b"], "expected_versions": {"a": 2}}
    result = {"handles": [{"id": "a", "version": 1}, {"id": "b", "version": 1}], "context_chars": 100}
    measured = score(result, question, 3)
    assert measured["recall_at_k"] == .5
    assert measured["evidence_precision"] == .5
    assert measured["coverage"] == 0
    assert measured["stale_version_errors"] == 1
    empty = score({"handles": [], "context_chars": 2}, {"relevant_ids": [], "expected_versions": {}}, 3)
    assert empty["recall_at_k"] is None and empty["abstention_success"] == 1
    unsupported = score(result, {"relevant_ids": [], "expected_versions": {}}, 3)
    assert unsupported["abstention_success"] == 0
    summary = aggregate([dict(measured, method="pace", latency_ms=4, error=None),
                         {"method": "pace", "error": "failure"}], ("method",))[0]
    assert summary["errors"] == 1 and summary["samples"] == 2 and summary["p95_ms"] == 4


def test_strategies_preserve_budget_input_and_no_seed_abstention():
    state, questions = make_fixture(11, 3)
    before = digest(state)
    for method in METHODS:
        for question in (questions[0], questions[1], questions[6]):
            packet = Pace().retrieve(state, Recall(query=question["query"], dataset=question["dataset"],
                                                   strategy=method, budget_chars=2000))
            assert packet["context_chars"] <= 2000
            assert all(item["id"].startswith(question["dataset"]) for item in packet["handles"])
            if question["unanswerable"]:
                assert not packet["handles"]
    assert digest(state) == before


def test_results_replace_complete_json(tmp_path):
    import json
    path = tmp_path/"results.json"
    path.write_text('{"previous": true}', encoding="utf-8")
    write_results(path, {"status": "completed", "raw": ["one", "two"]})
    assert json.loads(path.read_text(encoding="utf-8")) == {"status": "completed", "raw": ["one", "two"]}
    assert not path.with_suffix(".json.tmp").exists()
