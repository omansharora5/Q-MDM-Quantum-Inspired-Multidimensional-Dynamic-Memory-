from test_contract import environment, headers

from mnemograph.retrieval import tokens

QUERY = "What changed about the travel plan?"


def test_extraction_rationale_and_retention(environment):
    client, _, _ = environment
    assert client.post("/api/demo", headers=headers(), json={"dataset": "personal-assistant"}).status_code == 200
    params = {"dataset": "personal-assistant"}
    result = client.get("/api/extraction", headers=headers(), params=params).json()
    assert result["dataset"] == "personal-assistant"
    messages = result["messages"]
    assert len(messages) == 10
    for message in messages:
        assert {"role", "user_stated", "cue_overlap", "change_words", "duplicate_of"} <= set(message["features"])
        assert message["rationale"]
    retained = [message for message in messages if message["retained"]]
    not_retained = [message for message in messages if not message["retained"]]
    assert retained and not_retained
    sample = retained[0]
    assert sample["memories"]
    expanded = client.get("/api/memories/" + sample["memories"][0]["id"], headers=headers()).json()
    assert expanded["payload"]["source_message_id"] == sample["id"]
    assert any(line.startswith("Became memory:") for line in sample["rationale"])

    # No seeded pair is >= 0.8 similar, so construct a duplicate fixture inline.
    def send(key, at):
        return client.post("/api/messages", headers=headers(), json={
            "role": "user", "text": "Book the express coach for the coastal weekend.", "at": at,
            "session_id": "duplicate-fixture", "dataset": "personal-assistant", "synthetic": True,
            "idempotency_key": key}).json()["id"]

    first = send("dup-1", "2026-10-20T09:00:00Z")
    second = send("dup-2", "2026-10-20T10:00:00Z")
    refreshed = client.get("/api/extraction", headers=headers(), params=params).json()["messages"]
    duplicate = next(message for message in refreshed if message["id"] == second)
    assert duplicate["features"]["duplicate_of"] == first
    assert "term overlap" in " ".join(duplicate["rationale"])
    assert next(message for message in refreshed if message["id"] == first)["features"]["duplicate_of"] is None


def test_recall_why_explains_selection(environment):
    client, _, _ = environment
    assert client.post("/api/demo", headers=headers(), json={"dataset": "personal-assistant"}).status_code == 200
    packet = client.post("/api/recall", headers=headers(),
                         json={"query": QUERY, "dataset": "personal-assistant"}).json()
    assert packet["handles"] and packet["context_chars"] <= packet["budget_chars"]
    state = client.get("/api/state", headers=headers(), params={"dataset": "personal-assistant"}).json()
    records = {record["id"]: record for record in state["memories"]}
    seed = next(handle for handle in packet["handles"] if handle["id"] in packet["seeds"])
    assert seed["why"]["via"] == "direct match" and len(seed["why"]["matched"]) <= 4
    assert seed["why"]["matched"]
    for handle in packet["handles"]:
        why = handle["why"]
        assert isinstance(why["intent_boost"], bool) and why["via"]
        payload = records[handle["id"]]["payload"]
        available = set(tokens(payload["title"] + " " + payload["content"] + " " + " ".join(payload["cues"])))
        assert all(term in available and term in tokens(QUERY) for term in why["matched"])
