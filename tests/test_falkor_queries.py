"""Query construction checks only. These tests do not run a Cypher engine."""

import json
from types import SimpleNamespace

import pytest

pytest.importorskip("falkordb")

from mnemograph.auth import DomainError, Scope
from mnemograph.falkor import FalkorStore, MEMORY_RELATIONS
from mnemograph.models import Memory
from mnemograph.store import fingerprint, prepare_forget


SCOPE = Scope("test", "query-contract", "owner", frozenset({"read", "write"}))


def record(entity_id, kind, payload, revision):
    return {"schema_version": 2, "id": entity_id, "kind": kind, "payload": payload,
            "version": 1, "revision": revision, "owner": "owner", "actor": "owner",
            "updated_at": "2026-10-18T00:00:00+00:00"}


def memory(**values):
    return Memory(title="Secret decision", content="Private original message",
                  source={"title": "Evidence", "text": "Private original message"}, **values).model_dump(mode="json")


def captured_store(monkeypatch, records):
    state = {"revision": max((r["revision"] for r in records), default=0),
             "entities": {r["id"]: r for r in records}, "history": records,
             "events": [], "receipts": {}}
    calls = []

    def capture(query, params=None, timeout=None):
        calls.append((query, params))
        return SimpleNamespace(result_set=[["saved"]])

    store = FalkorStore.__new__(FalkorStore)
    monkeypatch.setattr(store, "graph", lambda scope: SimpleNamespace(query=capture))
    monkeypatch.setattr(store, "snapshot", lambda scope: state)
    return store, calls, state


def test_typed_links_and_message_origin_are_parameterized(monkeypatch):
    targets = [record(f"target-{index}", "memory", memory(), index + 1) for index in range(len(MEMORY_RELATIONS))]
    message = record("message-origin", "message", {"text": "Private original message"}, 7)
    store, calls, _ = captured_store(monkeypatch, targets + [message])
    payload = memory(links=[{"target_id": target["id"], "relation": relation}
                            for target, relation in zip(targets, MEMORY_RELATIONS)],
                     source_message_id=message["id"], dataset="camera-lab")
    store.commit(SCOPE, "new-memory", "memory", payload, 0, "create", fingerprint(payload))
    assert len(calls) == 1
    query, params = calls[0]
    assert "WHERE p.revision=$base" in query and params["base"] == 7
    assert "Private original message" not in query and "camera-lab" not in query
    assert params["dataset"] == "camera-lab" and params["source_message"] == "message-origin"
    assert "MERGE (n)-[:SOURCED_FROM]->(m)" in query
    for index, relation in enumerate(MEMORY_RELATIONS):
        assert f"MERGE (n)-[:{relation}]->(l{index})" in query
        assert params[f"link{index}"] == targets[index]["id"]
        assert relation in query.split("OPTIONAL MATCH (n)-[old:")[1].split("]")[0]


def test_unknown_relation_cannot_be_interpolated_into_query(monkeypatch):
    store, calls, _ = captured_store(monkeypatch, [record("target", "memory", memory(), 1)])
    payload = memory()
    payload["links"] = [{"target_id": "target", "relation": "SUPPORTS]->() DELETE n //"}]
    with pytest.raises(DomainError) as error:
        store.commit(SCOPE, "new-memory", "memory", payload, 0, "create", fingerprint(payload))
    assert error.value.status == 422
    assert calls == []


def test_adjacency_union_has_matching_columns_and_typed_edges(monkeypatch):
    store = FalkorStore.__new__(FalkorStore)
    calls = []

    def capture(query, timeout):
        calls.append(query)
        return SimpleNamespace(result_set=[["source", "target", "SUPPORTS"]])

    monkeypatch.setattr(store, "graph", lambda scope: SimpleNamespace(query=capture))
    assert store.adjacency(SCOPE) == {"source": {"target": "SUPPORTS"}}
    assert calls[0].count("AS relation") == 2
    assert all(relation in calls[0] for relation in MEMORY_RELATIONS)


def test_forget_redacts_histories_and_sources_in_one_guarded_query(monkeypatch):
    message = record("message", "message", {"text": "Private original message"}, 1)
    original = record("original", "memory", memory(source_message_id="message", cues=["private topic"]), 2)
    derivative = record("derived", "memory", memory(links=[{"target_id": "original", "relation": "DERIVED_FROM"}]), 3)
    trace = record("trace", "trace", {"handles": [{"path": ["derived", "original"]}]}, 4)
    unrelated = record("unrelated", "memory", memory(), 5)
    store, calls, _ = captured_store(monkeypatch, [message, original, derivative, trace, unrelated])
    receipt = store.forget(SCOPE, "original", 1, "forget-1")
    assert receipt["forgotten_ids"] == ["derived", "message", "original", "trace"]
    assert len(calls) == 1
    query, params = calls[0]
    assert "WHERE p.revision=$base" in query and params["base"] == 5 and params["revision"] == 6
    assert {item["id"] for item in params["redactions"]} == set(receipt["forgotten_ids"])
    assert all(json.loads(item["record"])["payload"] == {"deleted": True} for item in params["redactions"])
    assert "Private original message" not in json.dumps(params)
    assert "OPTIONAL MATCH (v:Revision)-[:CHANGED]->(n)" in query
    assert "SET v.record=item.record" in query
    assert "OPTIONAL MATCH (v)-[:EVIDENCED_BY]->(s:Source)" in query
    assert query.index("DETACH DELETE s") < query.index("OPTIONAL MATCH (n)-[old]-()")
    assert "DELETE old" in query and "n.title='Forgotten'" in query
    assert params["forgotten_cues"] == ["private topic"]
    assert "c.name IN $forgotten_cues AND NOT (c)--()" in query
    assert "CREATE (e:Event" in query and "CREATE (r:WriteReceipt" in query
    assert json.loads(params["receipt"])["receipt"] == receipt


def test_forget_retry_returns_existing_receipt_without_another_write(monkeypatch):
    original = record("original", "memory", memory(), 1)
    store, calls, state = captured_store(monkeypatch, [original])
    receipt, change = prepare_forget(state, SCOPE, "original", 1, "forget-1")
    state["receipts"][change["receipt_key"]] = {"request_hash": change["request_hash"], "receipt": receipt}
    assert store.forget(SCOPE, "original", 1, "forget-1") == receipt
    assert calls == []
