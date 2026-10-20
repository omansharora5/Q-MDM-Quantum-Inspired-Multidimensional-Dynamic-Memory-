import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .auth import DomainError, Scope
from .models import now
from .policy import validate_write, owner, references


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def source_digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Store(Protocol):
    name: str

    def snapshot(self, scope: Scope) -> dict: ...

    def commit(self, scope: Scope, entity_id: str, kind: str, payload: dict,
               expected: int, key: str, request_hash: str) -> dict: ...


def prepare(state, scope, entity_id, kind, payload, expected, key, request_hash):
    receipt_key = fingerprint([scope.agent, key])
    existing = state["receipts"].get(receipt_key)
    if existing:
        if existing["request_hash"] != request_hash:
            raise DomainError(409, "Idempotency key already used with different input")
        return existing["receipt"], None
    current = state["entities"].get(entity_id)
    validate_write(state, scope, entity_id, kind, payload, current)
    version = current["version"] if current else 0
    if version != expected:
        raise DomainError(409, f"Version conflict: expected {expected}, current {version}")
    if current and current["kind"] != kind:
        raise DomainError(409, "An entity cannot change type")
    if kind == "task" and current and scope.agent not in (current["payload"]["target_agent"], owner(current)):
        raise DomainError(403, "Only the task owner or handoff author can update it")
    if kind == "lease":
        task = state["entities"].get(payload["task_id"])
        if not task or task["kind"] != "task" or task["payload"]["target_agent"] != scope.agent:
            raise DomainError(403, "Only the assigned agent can claim this task")
        if task["version"] != payload["expected_task_version"]:
            raise DomainError(409, "Task changed before the claim")
        if current and datetime.fromisoformat(current["payload"]["expires_at"]) > datetime.now(timezone.utc) and current["actor"] != scope.agent:
            raise DomainError(409, "Task already has an active lease")
    if kind == "action":
        lease = state["entities"].get("lease-"+payload["task_id"])
        if not lease or lease["actor"] != scope.agent or lease["version"] != payload["fencing_token"] or datetime.fromisoformat(lease["payload"]["expires_at"]) <= datetime.now(timezone.utc):
            raise DomainError(409, "Task lease expired or fencing token is stale")
        task = state["entities"].get(payload["task_id"])
        if not task or task["version"] != lease["payload"]["expected_task_version"] or task["payload"]["target_agent"] != scope.agent or task["payload"]["status"] == "completed":
            raise DomainError(409, "Task changed after the lease was issued")
    references = payload.get("related_ids", []) if kind == "memory" else payload.get("memory_ids", [])
    for reference in references:
        target = state["entities"].get(reference)
        if not target or target["kind"] != "memory":
            raise DomainError(404, "A referenced memory is unavailable in this project")
    revision = state["revision"] + 1
    record = {"schema_version": 2, "id": entity_id, "kind": kind, "payload": payload, "version": version + 1,
              "owner": owner(current) if current else scope.agent,
              "actor": scope.agent, "updated_at": now(), "revision": revision}
    receipt = {"id": entity_id, "version": version + 1, "revision": revision}
    event = {"revision": revision, "action": payload.get("action", f"{kind}.saved"),
             "actor": scope.agent, "entity_id": entity_id, "at": record["updated_at"],
             "version": version + 1, "dataset": payload.get("dataset", "workspace")}
    return receipt, {"record": record, "event": event, "receipt_key": receipt_key,
                     "request_hash": request_hash, "receipt": receipt}


def prepare_forget(state, scope, entity_id, expected, key):
    request_hash = fingerprint(["forget", entity_id, expected])
    receipt_key = fingerprint([scope.agent, key])
    existing = state["receipts"].get(receipt_key)
    if existing:
        if existing["request_hash"] != request_hash:
            raise DomainError(409, "Idempotency key already used with different input")
        return existing["receipt"], None
    current = state["entities"].get(entity_id)
    if not current or current["kind"] != "memory":
        raise DomainError(404, "Memory is unavailable in this project")
    if owner(current) != scope.agent:
        raise DomainError(403, "Only the memory owner can permanently forget it")
    if current["version"] != expected:
        raise DomainError(409, "Version conflict while forgetting memory")
    removed = {entity_id}
    source_ids = {record["payload"].get("source_message_id") for record in [current, *state["history"]]
                  if record["id"] == entity_id and record["kind"] == "memory"}
    source_ids.discard(None)
    owned_sources = {key for key in source_ids if owner(state["entities"][key]) == scope.agent}
    removed |= owned_sources
    while True:
        derived = {key for key, record in state["entities"].items()
                   if references(record["payload"]) & removed or record["payload"].get("memory_id") in removed
                   or (record["kind"] == "trace" and any(set(h["path"]) & removed for h in record["payload"].get("handles", [])))}
        if derived <= removed:
            break
        removed |= derived
    revision, at = state["revision"] + 1, now()
    tombstones = {key: {"schema_version": 2, "id": key, "kind": "tombstone", "payload": {"deleted": True},
                        "owner": owner(state["entities"][key]), "actor": scope.agent, "version": state["entities"][key]["version"] + 1,
                        "revision": revision, "updated_at": at} for key in sorted(removed)}
    receipt = {"id": entity_id, "version": expected + 1, "revision": revision, "deleted": True, "forgotten_ids": sorted(removed),
               "retained_source_ids": sorted(source_ids-owned_sources)}
    event = {"revision": revision, "action": "memory.forgotten", "actor": scope.agent, "entity_id": entity_id, "at": at}
    return receipt, {"tombstones": tombstones, "event": event, "receipt_key": receipt_key,
                     "request_hash": request_hash, "receipt": receipt}


class SQLiteStore:
    name = "sqlite-development"

    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS revisions (
                    scope TEXT, revision INTEGER, entity_id TEXT, record TEXT, event TEXT,
                    PRIMARY KEY(scope, revision));
                CREATE TABLE IF NOT EXISTS entities (
                    scope TEXT, id TEXT, record TEXT, PRIMARY KEY(scope,id));
                CREATE TABLE IF NOT EXISTS receipts (
                    scope TEXT, key TEXT, hash TEXT, receipt TEXT, PRIMARY KEY(scope,key));
            """)

    def connection(self):
        return sqlite3.connect(self.path, timeout=15)

    def _snapshot(self, db, scope):
        # shortcut: load a small project snapshot, add indexed candidate queries before large-project deployment.
        namespace = scope.namespace
        records = [json.loads(row[0]) for row in db.execute("SELECT record FROM entities WHERE scope=?", (namespace,))]
        events = [json.loads(row[0]) for row in db.execute("SELECT event FROM revisions WHERE scope=? ORDER BY revision", (namespace,))]
        history = [json.loads(row[0]) for row in db.execute("SELECT record FROM revisions WHERE scope=? ORDER BY revision", (namespace,))]
        receipts = {key: {"request_hash": hashed, "receipt": json.loads(receipt)} for key, hashed, receipt in
                    db.execute("SELECT key,hash,receipt FROM receipts WHERE scope=?", (namespace,))}
        return {"revision": events[-1]["revision"] if events else 0, "entities": {r["id"]: r for r in records},
                "events": events, "history": history, "receipts": receipts}

    def snapshot(self, scope):
        with self.connection() as db:
            db.execute("BEGIN")
            return self._snapshot(db, scope)

    def commit(self, scope, entity_id, kind, payload, expected, key, request_hash):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            receipt, change = prepare(self._snapshot(db, scope), scope, entity_id, kind, payload, expected, key, request_hash)
            if change:
                record = change["record"]
                db.execute("INSERT OR REPLACE INTO entities VALUES (?,?,?)", (scope.namespace, entity_id, encode(record)))
                db.execute("INSERT INTO revisions VALUES (?,?,?,?,?)", (scope.namespace, record["revision"], entity_id,
                                                                      encode(record), encode(change["event"])))
                db.execute("INSERT INTO receipts VALUES (?,?,?,?)", (scope.namespace, change["receipt_key"], request_hash, encode(receipt)))
            return receipt

    def forget(self, scope, entity_id, expected, key):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            receipt, change = prepare_forget(self._snapshot(db, scope), scope, entity_id, expected, key)
            if change:
                for removed_id, record in change["tombstones"].items():
                    db.execute("UPDATE entities SET record=? WHERE scope=? AND id=?", (encode(record), scope.namespace, removed_id))
                    db.execute("UPDATE revisions SET record=? WHERE scope=? AND entity_id=?", (encode(record), scope.namespace, removed_id))
                record = change["tombstones"][entity_id]
                db.execute("INSERT INTO revisions VALUES (?,?,?,?,?)", (scope.namespace, receipt["revision"], entity_id, encode(record), encode(change["event"])))
                db.execute("INSERT INTO receipts VALUES (?,?,?,?)", (scope.namespace, change["receipt_key"], change["request_hash"], encode(receipt)))
            return receipt
