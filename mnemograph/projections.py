from datetime import datetime

from .policy import dataset_of
from .store import fingerprint, source_digest

DATASETS = {"personal-assistant": "Everyday assistant", "camera-lab": "Camera lab", "team-planning": "Team planning", "workspace": "Workspace", "system-design": "Earlier design sample"}
LAYERS = {"semantic": {"project", "cue", "fact", "decision", "core", "insight", "hypothesis", "resource", "procedure", "episode"},
          "temporal": {"revision", "message"}, "provenance": {"source", "message"}, "collaboration": {"agent", "task", "checkpoint"}}


def instant(value):
    return datetime.fromisoformat(value).timestamp()


def knowledge_revision(state):
    return max((r["revision"] for r in state["history"] if r["kind"] in ("memory", "message", "task", "checkpoint", "tombstone")), default=0)


def original_message(record, entities):
    payload = record["payload"]
    linked = entities.get(payload.get("source_message_id"))
    if linked:
        message = linked["payload"]
        return {"text": message["text"], "at": message["at"], "speaker": message["role"], "platform": message["platform"]}
    source = payload.get("source", {})
    return {"text": source.get("text", payload.get("text", payload.get("context", payload.get("objective", "")))),
            "at": source.get("occurred_at") or payload.get("at") or record["updated_at"],
            "speaker": source.get("speaker", payload.get("role", record["actor"])),
            "platform": source.get("platform", payload.get("platform", "memory-service"))}


def graph_view(state, project, revision=None):
    historical = revision is not None
    if historical:
        entities = {}
        for record in sorted(state["history"], key=lambda r: r["revision"]):
            if record["revision"] <= revision:
                entities[record["id"]] = record
        state = {**state, "entities": entities, "history": [r for r in state["history"] if r["revision"] <= revision]}
    entities, nodes, edges = state["entities"], {}, []
    messages = [original_message(r, entities) for r in entities.values() if r["kind"] in ("memory", "message")]
    last_message = max(messages, key=lambda message: instant(message["at"])) if messages else None

    def node(key, label, kind, **fields):
        nodes.setdefault(key, {"id": key, "label": label, "type": kind, "updated_at": fields.get("updated_at"),
                               "latest_message": fields.get("latest_message"), **fields})
        incoming, current = fields.get("latest_message"), nodes[key].get("latest_message")
        if incoming and (not current or instant(incoming["at"]) > instant(current["at"])):
            nodes[key]["latest_message"] = incoming
        if "record" in fields and kind == "agent":
            nodes[key]["record"] = fields["record"]

    def edge(source, target, kind):
        value = {"source": source, "target": target, "type": kind}
        if value not in edges:
            edges.append(value)

    node("project", project, "project", latest_message=last_message)
    for record in entities.values():
        key, kind, payload = record["id"], record["kind"], record["payload"]
        message = original_message(record, entities)
        if kind == "memory":
            node(key, payload["title"], payload["kind"], record=record, updated_at=record["updated_at"],
                 latest_message=message, source_hash=source_digest(payload["source"]["text"]), dataset=dataset_of(record))
            edge("project", key, "ABOUT")
            source_id = f"source-{key}-v{record['version']}"
            node(source_id, payload["source"]["title"], "source", parent=key, detail=payload["source"]["text"],
                 latest_message=message, updated_at=record["updated_at"], source_hash=source_digest(payload["source"]["text"]))
            edge(key, source_id, "EVIDENCED_BY")
            author = "agent-" + record["actor"]
            node(author, record["actor"], "agent", latest_message=message, updated_at=record["updated_at"])
            edge(key, author, "AUTHORED_BY")
            for cue in payload.get("cues", []):
                cue_id = "cue-" + fingerprint(cue)[:12]
                node(cue_id, cue, "cue", latest_message=message, updated_at=record["updated_at"])
                edge(cue_id, key, "ASSOCIATED_WITH")
            for related in payload.get("related_ids", []):
                edge(key, related, "RELATED_TO")
            for link in payload.get("links", []):
                edge(key, link["target_id"], link["relation"])
            if payload.get("source_message_id"):
                edge(key, payload["source_message_id"], "SOURCED_FROM")
            for old in state["history"]:
                if old["id"] == key and old["kind"] == "memory":
                    version_id = f"version-{key}-v{old['version']}"
                    node(version_id, f"Version {old['version']} · {payload['title']}", "revision", parent=key,
                         record=old, latest_message=original_message(old, entities), updated_at=old["updated_at"])
                    edge(key, version_id, "HAS_REVISION")
        elif kind == "message":
            node(key, payload["role"] + ": " + payload["text"][:65], "message", record=record, latest_message=message,
                 updated_at=record["updated_at"], detail=payload["text"])
            edge("project", key, "HAS_MESSAGE")
        elif kind in ("task", "checkpoint"):
            node(key, payload.get("title", payload.get("objective", "Checkpoint")), kind, record=record,
                 latest_message=message, updated_at=record["updated_at"])
            edge("project", key, "COORDINATES")
            for memory_id in payload.get("memory_ids", []):
                edge(key, memory_id, "CONTEXT")
            if payload.get("target_agent"):
                target = "agent-" + payload["target_agent"]
                node(target, payload["target_agent"], "agent", latest_message=message, updated_at=record["updated_at"])
                edge(key, target, "ASSIGNED_TO")
        elif kind == "agent":
            node(key, record["actor"], "agent", record=record, latest_message=message, updated_at=record["updated_at"])
            edge("project", key, "WORKS_ON")
    edges = [e for e in edges if e["source"] in nodes and e["target"] in nodes]
    adjacency = {key: set() for key in nodes}
    for e in edges:
        adjacency[e["source"]].add(e["target"])
        adjacency[e["target"]].add(e["source"])
    for key, value in nodes.items():
        nearby = set(adjacency[key])
        for other in list(nearby):
            nearby |= adjacency[other]
        nearby.discard(key)
        value["facets"] = {layer: sorted(other for other in nearby if nodes[other]["type"] in kinds)[:40] for layer, kinds in LAYERS.items()}
    return {"nodes": list(nodes.values()), "edges": edges, "revision": state["revision"],
            "memory_revision": knowledge_revision(state), "historical": historical}
