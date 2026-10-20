from .auth import DomainError


def dataset_of(record):
    payload = record["payload"]
    if "dataset" in payload:
        return payload["dataset"]
    if payload.get("synthetic"):
        text = (payload.get("title", "") + " " + " ".join(payload.get("cues", []))).casefold()
        return "camera-lab" if any(word in text for word in ("camera", "calibration", "hardware")) else "system-design"
    return "workspace"


def owner(record):
    return record.get("owner", record["actor"])


def audience(record):
    if record["payload"].get("visibility", "shared") == "shared":
        return None
    return {owner(record), *record["payload"].get("shared_with", [])}


def can_read(record, agent):
    allowed = audience(record)
    return record["kind"] != "tombstone" and (allowed is None or agent in allowed)


def references(payload):
    return set(payload.get("related_ids", []) + payload.get("memory_ids", [])
               + [link["target_id"] for link in payload.get("links", [])]
               + ([payload["source_message_id"]] if payload.get("source_message_id") else [])
               + ([payload["task_id"]] if payload.get("task_id") else []))


def visible_snapshot(state, scope, dataset=None):
    visible = {key: record for key, record in state["entities"].items() if can_read(record, scope.agent)}
    while True:
        hidden = set(state["entities"]) - set(visible)
        blocked = [key for key, record in visible.items() if references(record["payload"]) & hidden
                   or (record["kind"] == "trace" and any(set(handle["path"]) & hidden for handle in record["payload"].get("handles", [])))
                   or record["payload"].get("memory_id") in hidden]
        if not blocked:
            break
        for key in blocked:
            visible.pop(key)
    if dataset:
        visible = {key: record for key, record in visible.items()
                   if dataset_of(record) == dataset or record["kind"] == "agent"}
    ids = set(visible)
    return {**state, "entities": visible, "history": [r for r in state["history"] if r["id"] in ids],
            "events": [e for e in state["events"] if e["entity_id"] in ids], "receipts": {}}


def validate_write(state, scope, entity_id, kind, payload, current):
    if current and not can_read(current, scope.agent):
        raise DomainError(404, "Record is unavailable in this project")
    if current and (audience(current) is not None or payload.get("visibility", "shared") != current["payload"].get("visibility", "shared")
                    or payload.get("shared_with", []) != current["payload"].get("shared_with", [])) and scope.agent != owner(current):
        raise DomainError(403, "Only the owner can change sharing or revise private memory")
    new_record = {"actor": scope.agent, "owner": owner(current) if current else scope.agent, "kind": kind, "payload": payload}
    permitted = audience(new_record)
    allowed_ids = set(visible_snapshot(state, scope)["entities"])
    for reference in references(payload):
        target = state["entities"].get(reference)
        if not target or reference not in allowed_ids:
            raise DomainError(404, "A referenced record is unavailable in this project")
        if any(link["target_id"] == reference for link in payload.get("links", [])) and target["kind"] != "memory":
            raise DomainError(422, "Typed memory relationships must point to another memory")
        source_audience = audience(target)
        if source_audience is not None and (permitted is None or not permitted <= source_audience):
            raise DomainError(403, "Derived memory cannot broaden its source's visibility")
        if kind == "task" and source_audience is not None and payload["target_agent"] not in source_audience:
            raise DomainError(403, "The receiving agent cannot access this memory")
    if kind == "memory" and payload.get("source_message_id"):
        message = state["entities"][payload["source_message_id"]]
        if message["kind"] != "message" or payload["source"]["text"] not in message["payload"]["text"]:
            raise DomainError(422, "Source text must quote the referenced original message")
    if kind == "memory":
        pending = [link["target_id"] for link in payload.get("links", []) if link["relation"] == "SUPERSEDES"]
        seen = set()
        while pending:
            target_id = pending.pop()
            if target_id == entity_id:
                raise DomainError(422, "Supersession relationships must not form a cycle")
            if target_id in seen:
                continue
            seen.add(target_id)
            pending.extend(link["target_id"] for link in state["entities"][target_id]["payload"].get("links", []) if link["relation"] == "SUPERSEDES")
    if kind == "memory" and payload.get("claim_key") and payload.get("status") == "accepted":
        supersedes = {link["target_id"] for link in payload.get("links", []) if link["relation"] == "SUPERSEDES"}
        replaced = supersedes | {link["target_id"] for record in state["entities"].values() if record["id"] != entity_id and record["kind"] == "memory"
                    and record["payload"].get("status") == "accepted"
                    for link in record["payload"].get("links", []) if link["relation"] == "SUPERSEDES"}
        for other_id, record in state["entities"].items():
            other = record["payload"]
            if other_id != entity_id and other_id not in replaced and record["kind"] == "memory" and other.get("status") == "accepted" and other.get("dataset", "workspace") == payload.get("dataset", "workspace") and other.get("claim_key") == payload["claim_key"] and other.get("claim_value") != payload.get("claim_value") and other_id not in supersedes:
                if can_read(record, scope.agent):
                    raise DomainError(409, "Conflicting accepted claim; propose a disputed candidate or link an explicit supersession")
                raise DomainError(409, "This claim cannot be promoted under the current scope")
