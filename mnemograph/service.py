from datetime import datetime, timezone, timedelta
from uuid import uuid4

from .auth import DomainError
from .models import Connect, Handoff, Recall, Write, Message
from .retrieval import Pace, memories_at, terms
from .store import fingerprint, source_digest
from .policy import visible_snapshot, can_read, dataset_of
from .projections import graph_view, knowledge_revision, DATASETS, original_message, instant

CHANGE_WORDS = ("instead", "closed", "change", "now", "unavailable", "should")


class MemoryService:
    def __init__(self, store, credentials, strategy=None):
        self.store, self.credentials = store, credentials
        self.strategy = strategy or Pace()

    def view(self, scope, dataset=None):
        state = visible_snapshot(self.store.snapshot(scope), scope, dataset)
        for group in ("entities", "history"):
            values = state[group].values() if group == "entities" else state[group]
            normalized = [{**record, "payload": {"dataset": dataset_of(record), **record["payload"]}} for record in values]
            state[group] = {record["id"]: record for record in normalized} if group == "entities" else normalized
        return state

    def save(self, scope, command: Write, memory_id=None):
        if memory_id is None and command.expected_version:
            raise DomainError(422, "New memories require expected_version=0")
        if memory_id is not None and command.expected_version == 0:
            raise DomainError(422, "Updates require the last observed expected_version")
        entity_id = memory_id or "m-" + fingerprint([scope.agent, command.idempotency_key])[:16]
        payload = command.memory.model_dump(mode="json")
        if payload["status"] == "accepted" and "coordinate" not in scope.actions:
            raise DomainError(403, "Promoting a memory requires the coordinate grant")
        if any(agent not in self.credentials.agents(scope) for agent in payload["shared_with"]):
            raise DomainError(404, "Shared reader is not provisioned in this project")
        return self.store.commit(scope, entity_id, "memory", payload, command.expected_version,
                                 command.idempotency_key, fingerprint(["save", memory_id, command.model_dump(mode="json")]))

    def expand(self, scope, memory_id, version=None):
        state = self.view(scope)
        record = state["entities"].get(memory_id)
        if version is not None:
            record = next((item for item in state["history"] if item["id"] == memory_id and item["version"] == version), None)
        if not record or record["kind"] != "memory":
            raise DomainError(404, "Memory is unavailable in this project")
        self.activity(scope, "memory.expanded", {"memory_id": memory_id, "version": record["version"]})
        return {**record, "source_hash": source_digest(record["payload"]["source"]["text"]),
                "latest_message": original_message(record, state["entities"]),
                "history": [{"version": item["version"], "at": item["updated_at"], "actor": item["actor"]}
                                     for item in state["history"] if item["id"] == memory_id]}

    def activity(self, scope, action, details):
        entity_id = "e-" + uuid4().hex
        return self.store.commit(scope, entity_id, "activity", {"action": action, **details}, 0, entity_id, fingerprint(details))

    def recall(self, scope, request: Recall):
        snapshot = self.view(scope)
        # Native adjacency is intersected with authorized IDs before ranking.
        adjacency = self.store.adjacency(scope) if hasattr(self.store, "adjacency") else None
        packet = self.strategy.retrieve(snapshot, request, adjacency)
        if request.cursor:
            cursor = snapshot["entities"].get(request.cursor)
            if not cursor or cursor["kind"] != "trace" or cursor["actor"] != scope.agent or cursor["payload"]["query"] != request.query:
                raise DomainError(404, "Retrieval cursor is unavailable for this query and agent")
            known = {handle["id"] for handle in cursor["payload"]["handles"]}
            packet["already_seen"] = sorted(known)
            packet["knowledge_changed"] = cursor["payload"].get("memory_revision") != knowledge_revision(snapshot)
        packet["memory_revision"] = knowledge_revision(snapshot)
        trace_id = "q-" + uuid4().hex
        self.store.commit(scope, trace_id, "trace", {"query": request.query, **packet}, 0, trace_id, fingerprint(packet))
        return {"trace_id": trace_id, "continuation": trace_id, **packet}

    def context(self, scope):
        state = self.view(scope)
        current = [record for record in memories_at(state).values() if record["payload"]["status"] == "accepted"]
        return {"project": scope.project, "revision": state["revision"], "strategy": self.strategy.name,
                "handles": [{"id": record["id"], "title": record["payload"]["title"], "version": record["version"]}
                            for record in sorted(current, key=lambda record: -record["revision"])[:6]],
                "checkpoints": [{"id": record["id"], **record["payload"]} for record in state["entities"].values()
                                if record["kind"] == "checkpoint" and record["actor"] == scope.agent][-1:],
                "tasks": [{"id": task["id"], "title": task["payload"]["title"], "version": task["version"],
                           "status": task["payload"]["status"]} for task in state["entities"].values()
                          if task["kind"] == "task" and task["payload"]["target_agent"] == scope.agent
                          and task["payload"]["status"] != "completed"][:10],
                "next": "Use memory_recall for task-relevant handles, then memory_expand for source evidence."}

    def connect(self, scope, request: Connect):
        entity_id = "agent-" + scope.agent
        state = self.store.snapshot(scope)
        current = state["entities"].get(entity_id)
        expected = current["version"] if current else 0
        return self.store.commit(scope, entity_id, "agent", request.model_dump(), expected, uuid4().hex, fingerprint(request.model_dump()))

    def handoff(self, scope, command: Handoff, task_id=None):
        if command.target_agent not in self.credentials.agents(scope):
            raise DomainError(404, "Target agent is not provisioned for this project")
        if task_id is None and command.expected_version:
            raise DomainError(422, "New handoffs require expected_version=0")
        if task_id is not None and command.expected_version == 0:
            raise DomainError(422, "Updates require expected_version")
        entity_id = task_id or "t-" + fingerprint([scope.agent, command.idempotency_key])[:16]
        return self.store.commit(scope, entity_id, "task", command.model_dump(), command.expected_version,
                                 command.idempotency_key, fingerprint(["handoff", task_id, command.model_dump()]))

    def state(self, scope, dataset=None):
        all_state = self.view(scope)
        state = self.view(scope, dataset) if dataset else all_state
        groups = {kind: [] for kind in ("memory", "task", "agent", "trace", "message", "checkpoint", "lease", "action")}
        for record in state["entities"].values():
            if record["kind"] in groups:
                groups[record["kind"]].append(record)
        agents = []
        for agent_id in self.credentials.agents(scope):
            record = next((item for item in groups["agent"] if item["actor"] == agent_id), None)
            recent = record and (datetime.now(timezone.utc) - datetime.fromisoformat(record["updated_at"])).total_seconds() < 90
            agents.append({"id": agent_id, "status": "active" if recent else "idle" if record else "not_connected",
                           "platform": record["payload"]["platform"] if record else None,
                           "context": record["payload"]["context"] if record else "",
                           "last_seen": record["updated_at"] if record else None})
        datasets = {}
        for record in all_state["entities"].values():
            if record["kind"] in ("memory", "message"):
                key = dataset_of(record)
                item = datasets.setdefault(key, {"id": key, "label": DATASETS.get(key, key), "memories": 0, "synthetic": True})
                item["memories"] += int(record["kind"] == "memory")
                item["synthetic"] = item["synthetic"] and record["payload"].get("synthetic", False)
        return {"schema_version": 2, "tenant": scope.tenant, "project": scope.project, "agent": scope.agent,
                "storage": self.store.name, "revision": state["revision"], "memories": groups["memory"],
                "memory_revision": knowledge_revision(state), "datasets": list(datasets.values()), "messages": groups["message"],
                "checkpoints": groups["checkpoint"], "leases": groups["lease"], "actions": groups["action"],
                "experiments_available": self.experiments()["status"] in ("completed", "completed_with_errors"),
                "tasks": groups["task"], "agents": agents, "traces": sorted(groups["trace"], key=lambda item: -item["revision"])[:30],
                "events": state["events"][-50:], "strategy": self.strategy.name}

    def graph(self, scope, dataset=None, revision=None):
        return graph_view(self.view(scope, dataset), scope.project, revision)

    def timeline(self, scope, dataset=None):
        state = self.view(scope, dataset)
        messages = []
        for record in state["entities"].values():
            if record["kind"] == "message":
                ids = [key for key, memory in state["entities"].items() if memory["payload"].get("source_message_id") == record["id"]]
                messages.append({"id": record["id"], **record["payload"], "memory_ids": ids})
            elif record["kind"] == "memory" and not record["payload"].get("source_message_id"):
                source = record["payload"]["source"]
                messages.append({"id": "source-"+record["id"], "role": source.get("speaker", record["actor"]), "text": source["text"],
                                 "at": source.get("occurred_at") or record["updated_at"], "platform": source.get("platform", "manual"),
                                 "session_id": source.get("session_id", ""), "memory_ids": [record["id"]],
                                 "synthetic": record["payload"].get("synthetic", False), "dataset": dataset_of(record)})
        return {"messages": sorted(messages, key=lambda value: instant(value["at"])), "changes": state["events"][-100:],
                "revision": state["revision"], "memory_revision": knowledge_revision(state)}

    def extraction(self, scope, dataset=None):
        """Deterministic retrospective rationale for message retention.

        Computed from the visible snapshot with fixed lexical rules (role, cue overlap, change
        words, term-duplicate detection) over curated synthetic demo data. This is an explanatory
        projection, not a trained importance classifier and makes no model calls.
        """
        state = self.view(scope, dataset)
        memories = [record for record in state["entities"].values() if record["kind"] == "memory"]
        cue_terms = {term for record in memories for term in terms(" ".join(record["payload"].get("cues", [])))}
        messages = sorted((record for record in state["entities"].values() if record["kind"] == "message"),
                          key=lambda record: (instant(record["payload"]["at"]), record["id"]))
        results, prior_terms = [], {}
        for record in messages:
            payload = record["payload"]
            message_terms = terms(payload["text"])
            linked = sorted((memory for memory in memories if memory["payload"].get("source_message_id") == record["id"]),
                            key=lambda memory: memory["id"])
            user_stated = payload["role"] in ("user", "human")
            overlap = sorted(message_terms & cue_terms)[:6]
            changes = [word for word in CHANGE_WORDS if word in message_terms]
            duplicate_of, duplicate_score = None, 0.
            # ponytail: O(n^2) pairwise Jaccard; fine at demo-snapshot scale, index term sets if this grows.
            for earlier_id, earlier in prior_terms.items():
                score = len(message_terms & earlier) / (len(message_terms | earlier) or 1)
                if score >= .8 and score > duplicate_score:
                    duplicate_of, duplicate_score = earlier_id, score
            prior_terms[record["id"]] = message_terms
            rationale = []
            if linked:
                rationale += [f"Became memory: '{memory['payload']['title']}' ({memory['payload']['kind']})" for memory in linked]
                if user_stated:
                    rationale.append("User-stated source; this retrospective view did not calculate a retention score")
                if overlap:
                    rationale.append("Shares cues with stored memories: " + ", ".join(overlap))
                if changes:
                    rationale.append("States a change or decision: " + ", ".join(changes))
            else:
                rationale.append("No memory was derived from this message")
                rationale.append("Shares cues but was not promoted" if overlap else "No cue overlap with stored memories")
            if duplicate_of:
                rationale.append(f"Repeat of earlier message ({round(duplicate_score*100)}% term overlap)")
            results.append({"id": record["id"], "role": payload["role"], "at": payload["at"], "platform": payload["platform"],
                            "text": payload["text"], "synthetic": payload.get("synthetic", False), "retained": bool(linked),
                            "memories": [{"id": memory["id"], "title": memory["payload"]["title"], "kind": memory["payload"]["kind"],
                                          "version": memory["version"]} for memory in linked],
                            "features": {"role": payload["role"], "user_stated": user_stated, "cue_overlap": overlap,
                                         "change_words": changes, "duplicate_of": duplicate_of},
                            "rationale": rationale})
        return results

    def ingest_message(self, scope, command: Message):
        entity_id = "msg-" + fingerprint([scope.agent, command.idempotency_key])[:16]
        payload = command.model_dump(mode="json", exclude={"idempotency_key"})
        return self.store.commit(scope, entity_id, "message", payload, 0, command.idempotency_key, fingerprint(["message", payload]))

    def checkpoint(self, scope, command):
        payload = command.model_dump(exclude={"idempotency_key"})
        entity_id = "cp-" + fingerprint([scope.agent, command.idempotency_key])[:16]
        return self.store.commit(scope, entity_id, "checkpoint", payload, 0, command.idempotency_key, fingerprint(["checkpoint", payload]))

    def claim(self, scope, task_id, command):
        state = self.view(scope)
        current = state["entities"].get("lease-"+task_id)
        payload = {"task_id": task_id, "expected_task_version": command.expected_task_version,
                   "expires_at": (datetime.now(timezone.utc)+timedelta(seconds=command.lease_seconds)).isoformat()}
        receipt = self.store.commit(scope, "lease-"+task_id, "lease", payload, current["version"] if current else 0,
                                    command.idempotency_key, fingerprint(["claim",task_id,command.model_dump()]))
        return {**receipt, "fencing_token": receipt["version"]}

    def ack_action(self, scope, command):
        entity_id = "action-"+fingerprint([command.task_id, command.action_id])[:16]
        payload = command.model_dump(exclude={"idempotency_key"})
        return self.store.commit(scope, entity_id, "action", payload, 0, command.idempotency_key, fingerprint(["action",payload]))

    def forget(self, scope, memory_id, command):
        return self.store.forget(scope, memory_id, command.expected_version, command.idempotency_key)

    def maintenance(self, scope):
        state = self.view(scope)
        groups = {}
        for record in state["entities"].values():
            if record["kind"] == "memory":
                groups.setdefault(fingerprint(record["payload"]["content"]), []).append(record["id"])
        return {"revision": state["revision"], "proposals": [{"action": "DUPLICATES", "memory_ids": ids,
                  "reason": "Exact matching content; inspect source and scope before consolidating"} for ids in groups.values() if len(ids)>1],
                "applied": False, "note": "Inspection only. Background maintenance never silently rewrites accepted evidence."}

    @staticmethod
    def experiments():
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / "artifacts" / "benchmarks" / "results.json"
        if not path.exists():
            return {"status": "not_run", "aggregate": [], "limitations": ["Run python -m benchmarks.run to generate local measurements."]}
        return {"status": "complete", **json.loads(path.read_text(encoding="utf-8"))}
