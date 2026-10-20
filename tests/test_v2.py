import hashlib
import json
from datetime import datetime, timezone

import pytest

from test_contract import environment, headers, memory, save
from mnemograph.retrieval import pagerank, quantum_walk


def test_personal_conversations_are_distinct_and_sources_are_exact(environment):
    client, _, _ = environment
    seeded = client.post("/api/demo", headers=headers(), json={"dataset":"personal-assistant"})
    assert seeded.status_code == 200, seeded.text
    state = client.get("/api/state", headers=headers(), params={"dataset":"personal-assistant"}).json()
    assert len(state["memories"]) == 6 and len(state["messages"]) == 10
    assert all(record["payload"]["synthetic"] for record in state["memories"]+state["messages"])
    timeline = client.get("/api/timeline", headers=headers(), params={"dataset":"personal-assistant"}).json()
    assert any(message["role"] == "user" and message["memory_ids"] for message in timeline["messages"])
    assert not client.get("/api/state", headers=headers(), params={"dataset":"camera-lab"}).json()["memories"]
    again = client.post("/api/demo", headers=headers(), json={"dataset":"personal-assistant"})
    assert again.json() == seeded.json()


def test_real_update_changes_links_and_preserves_original_history(environment):
    client, _, _ = environment
    seed = client.post("/api/demo",headers=headers(),json={"dataset":"personal-assistant"}).json()
    params = {"dataset":"personal-assistant"}
    before = client.get("/api/graph",headers=headers(),params=params).json()
    change = client.post("/api/demo/evolve",headers=headers(),json=params)
    assert change.status_code == 200, change.text
    changed = change.json()
    after = client.get("/api/graph",headers=headers(),params=params).json()
    old_edges = {(edge["source"],edge["target"],edge["type"]) for edge in before["edges"]}
    new_edges = {(edge["source"],edge["target"],edge["type"]) for edge in after["edges"]}
    assert old_edges-new_edges and new_edges-old_edges
    assert after["memory_revision"] > before["memory_revision"]
    node = next(node for node in after["nodes"] if node["id"] == changed["id"])
    assert "express coach" in node["latest_message"]["text"]
    assert node["record"]["version"] == 2
    assert client.get("/api/memories/"+changed["id"],headers=headers(),params={"version":1}).json()["payload"]["content"] == "The current weekend plan uses the Saturday train."
    assert client.post("/api/demo/evolve",headers=headers(),json=params).json() == changed
    old_graph = client.get("/api/graph",headers=headers(),params={**params,"revision":before["memory_revision"]}).json()
    assert old_graph["historical"]
    assert next(n for n in old_graph["nodes"] if n["id"]==changed["id"])["record"]["version"] == 1


def test_all_nodes_expose_real_facets_and_source_timestamps(environment):
    client, _, _ = environment
    client.post("/api/demo",headers=headers(),json={"dataset":"personal-assistant"})
    graph = client.get("/api/graph",headers=headers()).json()
    ids = {node["id"] for node in graph["nodes"]}
    assert {"source","cue","message","revision","agent","project"} <= {node["type"] for node in graph["nodes"]}
    for node in graph["nodes"]:
        assert set(node["facets"]) == {"semantic","temporal","provenance","collaboration"}
        assert all(set(values) <= ids for values in node["facets"].values())
        if node.get("latest_message"):
            assert datetime.fromisoformat(node["latest_message"]["at"]).tzinfo


def test_private_access_revocation_closes_direct_history_graph_trace_and_timeline(environment):
    client, _, _ = environment
    private = memory(title="Private launch note", visibility="private", shared_with=["developer"])
    saved = save(client,"private",private).json()
    assert client.get("/api/memories/"+saved["id"],headers=headers("b")).status_code == 200
    assert save(client,"bad-editor",private,"b",saved["id"],1).status_code == 403
    client.post("/api/recall",headers=headers("b"),json={"query":"launch note"})
    changed = save(client,"revoke",{**private,"shared_with":[]},"a",saved["id"],1)
    assert changed.status_code == 200
    for endpoint in ("/api/state","/api/graph","/api/timeline","/api/changes"):
        text = client.get(endpoint,headers=headers("b")).text
        assert "Private launch note" not in text and saved["id"] not in text
    assert client.get("/api/memories/"+saved["id"],headers=headers("b"),params={"version":1}).status_code == 404
    assert client.post("/api/recall",headers=headers("b"),json={"query":"launch note"}).json()["handles"] == []


def test_derivatives_cannot_broaden_private_source(environment):
    client, _, _ = environment
    private = save(client,"private",memory(visibility="private")).json()
    shared = save(client,"derived",memory(links=[{"target_id":private["id"],"relation":"DERIVED_FROM"}]))
    assert shared.status_code == 403
    assert save(client,"private-derived",memory(visibility="private",links=[{"target_id":private["id"],"relation":"DERIVED_FROM"}])).status_code == 201


def test_source_message_quote_and_promotion_are_governed(environment):
    client, _, _ = environment
    original = {"role":"user","text":"  Use the coach instead of the train.\n", "at":"2026-10-18T10:00:00+05:30",
                "session_id":"s-1","idempotency_key":"msg"}
    msg = client.post("/api/messages",headers=headers(),json=original).json()
    wrong = save(client,"invented",memory(source_message_id=msg["id"]))
    assert wrong.status_code == 422
    candidate = {"memory":memory(source_message_id=msg["id"],source={"title":"User","text":original["text"]}),"idempotency_key":"candidate"}
    proposed = client.post("/api/candidates",headers=headers(),json=candidate).json()
    full = client.get("/api/memories/"+proposed["id"],headers=headers()).json()
    assert full["payload"]["status"] == "asserted"
    assert full["latest_message"]["text"] == original["text"] == full["payload"]["source"]["text"]
    assert full["source_hash"] == hashlib.sha256(original["text"].encode()).hexdigest()
    assert save(client,"promote",{**full["payload"],"status":"accepted"},memory_id=proposed["id"],version=1).status_code == 200


def test_independent_agent_can_recall_an_exact_message_without_a_derived_memory(environment):
    client, _, _ = environment
    original = {"role":"user","text":"The shared transport note says use the express coach.",
                "at":"2026-10-18T10:00:00Z","session_id":"shared-chat","idempotency_key":"shared-message"}
    created = client.post("/api/messages",headers=headers(),json=original).json()
    packet = client.post("/api/recall",headers=headers("b"),json={"query":"express coach"}).json()
    assert packet["handles"] == []
    match = packet["messages"][0]
    assert match["id"] == created["id"] and match["text"] == original["text"]
    assert match["role"] == original["role"] and match["session_id"] == original["session_id"]
    assert not packet["insufficient_evidence"]
    trace = client.get("/api/state",headers=headers("b")).json()["traces"][-1]
    assert original["text"] not in str(trace) and trace["payload"]["message_ids"] == [created["id"]]


def test_supersession_is_explicit_and_current_recall_excludes_predecessor(environment):
    client, _, _ = environment
    first = save(client,"train",memory(claim_key="transport",claim_value="train")).json()
    conflict = save(client,"bus-bad",memory(content="Use a coach.",claim_key="transport",claim_value="coach"))
    assert conflict.status_code == 409
    second = save(client,"bus",memory(title="Coach approved",content="Use a coach.",claim_key="transport",claim_value="coach",
                  links=[{"target_id":first["id"],"relation":"SUPERSEDES"}])).json()
    packet = client.post("/api/recall",headers=headers(),json={"query":"cameras coach"}).json()
    assert second["id"] in {handle["id"] for handle in packet["handles"]}
    assert first["id"] not in {handle["id"] for handle in packet["handles"]}
    assert client.get("/api/memories/"+first["id"],headers=headers()).status_code == 200
    third = save(client,"walk",memory(title="Walk approved",content="Walk instead.",claim_key="transport",claim_value="walk",
                 links=[{"target_id":second["id"],"relation":"SUPERSEDES"}]))
    assert third.status_code == 201, third.text
    walk = client.get("/api/memories/"+third.json()["id"],headers=headers()).json()
    assert save(client,"drop-predecessor",{**walk["payload"],"links":[]},memory_id=walk["id"],version=1).status_code == 409
    assert save(client,"self-cycle",{**walk["payload"],"links":[{"target_id":walk["id"],"relation":"SUPERSEDES"}]},memory_id=walk["id"],version=1).status_code == 422


def test_forget_purges_linked_history_sources_and_retrieval_traces(environment):
    client, store, credentials = environment
    msg = client.post("/api/messages",headers=headers(),json={"role":"user","text":"Disposable canary 927481.","at":"2026-10-18T10:00:00Z","session_id":"erase","idempotency_key":"erase-msg"}).json()
    original = memory(content="Disposable canary 927481.",source_message_id=msg["id"],source={"title":"Canary","text":"Disposable canary 927481."})
    saved = save(client,"erase",original).json()
    derivative = save(client,"derived",memory(content="Disposable canary 927481.",links=[{"target_id":saved["id"],"relation":"DERIVED_FROM"}])).json()
    client.post("/api/recall",headers=headers(),json={"query":"canary"})
    command = {"expected_version":1,"idempotency_key":"forget"}
    forgotten = client.post("/api/memories/"+saved["id"]+"/forget",headers=headers(),json=command)
    assert forgotten.status_code == 200, forgotten.text
    assert {saved["id"],msg["id"],derivative["id"]} <= set(forgotten.json()["forgotten_ids"])
    raw = store.snapshot(credentials.authorize("a"))
    assert "Disposable canary 927481" not in json.dumps(raw)
    assert client.get("/api/memories/"+saved["id"],headers=headers(),params={"version":1}).status_code == 404
    assert client.post("/api/memories/"+saved["id"]+"/forget",headers=headers(),json=command).json() == forgotten.json()


def test_retrieval_cursor_checks_query_owner_and_freshness(environment):
    client, _, _ = environment
    save(client)
    result = client.post("/api/recall",headers=headers(),json={"query":"cameras"}).json()
    assert client.post("/api/recall",headers=headers("b"),json={"query":"cameras","cursor":result["continuation"]}).status_code == 404
    save(client,"another",memory(title="Another decision"))
    resumed = client.post("/api/recall",headers=headers(),json={"query":"cameras","cursor":result["continuation"]}).json()
    assert resumed["knowledge_changed"] and resumed["already_seen"]


def test_forget_does_not_erase_another_owners_original_message(environment):
    client, _, _ = environment
    text = "A shared original belongs to its writer."
    message = client.post("/api/messages",headers=headers(),json={"role":"user","text":text,"at":"2026-10-18T10:00:00Z","session_id":"ownership","idempotency_key":"source-owner"}).json()
    derived = save(client,"other-derived",memory(source_message_id=message["id"],source={"title":"Shared source","text":text}),token="b").json()
    forgotten = client.post("/api/memories/"+derived["id"]+"/forget",headers=headers("b"),json={"expected_version":1,"idempotency_key":"forget-other-derived"})
    assert forgotten.status_code == 200
    assert forgotten.json()["retained_source_ids"] == [message["id"]]
    assert text in client.get("/api/timeline",headers=headers()).text
    assert client.get("/api/memories/"+derived["id"],headers=headers()).status_code == 404


def test_task_fencing_rejects_stale_worker_and_action_retries_converge(environment):
    client, _, _ = environment
    command = {"title":"Work","target_agent":"developer","context":"Continue","memory_ids":[],"idempotency_key":"task"}
    task = client.post("/api/handoffs",headers=headers(),json=command).json()
    claim = {"expected_task_version":1,"idempotency_key":"claim1"}
    assert client.post("/api/handoffs/"+task["id"]+"/claim",headers=headers(),json=claim).status_code == 403
    first = client.post("/api/handoffs/"+task["id"]+"/claim",headers=headers("b"),json=claim).json()
    second = client.post("/api/handoffs/"+task["id"]+"/claim",headers=headers("b"),json={**claim,"idempotency_key":"claim2"}).json()
    action = {"task_id":task["id"],"fencing_token":first["fencing_token"],"action_id":"action-1","external_receipt":"Test artifact checked","idempotency_key":"ack"}
    assert client.post("/api/actions",headers=headers("b"),json=action).status_code == 409
    action["fencing_token"] = second["fencing_token"]
    accepted = client.post("/api/actions",headers=headers("b"),json=action)
    assert accepted.status_code == 201
    assert client.post("/api/actions",headers=headers("b"),json=action).json() == accepted.json()
    update = client.put("/api/handoffs/"+task["id"],headers=headers(),json={**command,"status":"completed","expected_version":1,"idempotency_key":"done"})
    assert update.status_code == 200
    assert client.post("/api/actions",headers=headers("b"),json={**action,"action_id":"late-action","idempotency_key":"late"}).status_code == 409


def test_latest_source_uses_timezone_instant_not_lexical_order(environment):
    client, _, _ = environment
    for i, at in enumerate(("2026-10-18T10:00:00+05:30", "2026-10-18T06:00:00Z")):
        response = client.post("/api/messages",headers=headers(),json={"role":"user","text":f"Event {i}","at":at,"session_id":"tz","idempotency_key":f"tz-{i}"})
        assert response.status_code == 201
    timeline = client.get("/api/timeline",headers=headers()).json()
    assert [m["text"] for m in timeline["messages"]] == ["Event 0", "Event 1"]
    graph = client.get("/api/graph",headers=headers()).json()
    assert next(n for n in graph["nodes"] if n["type"]=="project")["latest_message"]["text"] == "Event 1"


def test_quantum_and_pagerank_conserve_mass_and_do_not_turn_scores_into_truth():
    graph = {"a":{"b":"SUPPORTS"},"b":{"a":"SUPPORTS"},"isolated":{}}
    for algorithm in (pagerank,quantum_walk):
        scores = algorithm(graph,{"a":1.})
        assert sum(scores.values()) == pytest.approx(1.,abs=1e-8)
        assert all(value >= 0 for value in scores.values()) and scores["isolated"] == 0
