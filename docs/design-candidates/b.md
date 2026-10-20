# Candidate B: event-oriented memory with synchronous projections

## Usage (caller's view)

An agent connects once with a server-issued credential bound to its tenant, agent, allowed projects, and actions. The same credential works through REST or the local MCP bridge. The bridge reads its secret from the environment and never accepts identity overrides in tool arguments.

```python
# Custom or local API agent, ordinary HTTP client; no framework-specific SDK needed.
with httpx.Client(base_url=url, headers={"Authorization": f"Bearer {token}"}) as client:
    saved = client.post("/v1/projects/qc/memories", json={
        "kind": "decision", "summary": "Four cameras approved",
        "source": {"text": "Review accepted four cameras", "uri": "meeting:12"},
        "cues": ["camera mounting"], "idempotency_key": "meeting12-decision1"
    }).raise_for_status().json()
    packet = client.post("/v1/projects/qc/recall", json={
        "query": "Why avoid complex mounting?", "budget_chars": 3000
    }).raise_for_status().json()
    evidence = client.get(f"/v1/projects/qc/memories/{saved['memory_id']}").json()
```

MCP exposes `remember`, `recall`, `expand`, `update`, `handoff`, `state`, and `changes`; each maps errors and schemas to these HTTP operations. Codex and Claude Code configure the executable bridge and scoped environment credential. A custom agent exposes these functions as model tools, calls `state` before work, and writes verified results afterward. Memory use remains an agent policy; installation alone cannot capture conversation or force recall.

## Problem

Agents need a shared memory history whose current state and origin remain explainable after corrections. The graph UI also needs actual activity and context traces. A durable event per accepted operation gives both consumers the same history without introducing a message broker or a second authoritative database.

## Shape

```python
@dataclass(frozen=True)
class Scope:
    tenant_id: str; agent_id: str; projects: frozenset[str]; actions: frozenset[str]

@dataclass(frozen=True)
class Event:
    id: str; project_id: str; revision: int; kind: str
    aggregate_id: str; version: int; actor_id: str; recorded_at: str
    payload: dict  # validated discriminated payload at input; stored schema_version

@dataclass(frozen=True)
class WriteReceipt:
    event_id: str; memory_id: str; version: int; project_revision: int

@dataclass(frozen=True)
class RecallPacket:
    revision: int; strategy: str; handles: list[MemoryHandle]
    evidence_paths: list[EvidencePath]; truncated: bool; estimated_tokens: int

class MemoryService:
    def remember(self, scope: Scope, project: str, input: Remember) -> WriteReceipt: ...
    def update(self, scope: Scope, project: str, memory: str, input: Update) -> WriteReceipt: ...
    def handoff(self, scope: Scope, project: str, input: Handoff) -> WriteReceipt: ...
    def recall(self, scope: Scope, project: str, query: Recall) -> RecallPacket: ...
    def expand(self, scope: Scope, project: str, memory: str) -> MemoryEvidence: ...
    def state(self, scope: Scope, project: str) -> ProjectState: ...
    def changes(self, scope: Scope, project: str, after: int) -> ChangePage: ...

class Store(Protocol):
    def commit(self, scope: Scope, command: ValidatedCommand) -> WriteReceipt: ...
    def snapshot(self, scope: Scope, project: str, query: ReadQuery) -> ReadResult: ...

class RecallStrategy(Protocol):
    name: str
    def retrieve(self, graph: ScopedGraph, request: Recall) -> RecallPacket: ...
```

`MemoryService` owns validation, temporal claim semantics, and source requirements. `Store.commit` hides transaction and replay details. The caller supplies an expected aggregate version on update, never a project revision as a lock. Separate memories can change concurrently. Every write commits its event, updated memory projection, project revision, and idempotency receipt together. A duplicate key with identical canonical payload returns the original receipt; a changed payload returns 409. Scope for the key includes authenticated tenant, agent, project, and operation. Update mismatch returns 409 with the latest authorized version.

FalkorDB is the primary deployment store. Events, immutable memory revisions, source nodes, current memory projections, and graph links live together in the tenant graph. A guarded write must atomically check aggregate version and idempotency before creating the event and projection. That contract needs a real FalkorDB concurrency test before the adapter can claim it. A process-local lock alone is insufficient for independent server workers.

SQLite development mode uses one transaction with an event table, current-memory table, source table, and relationship table. It runs without Docker, marks every status response and dashboard with `storage=sqlite-development`, and makes no claim that FalkorDB paths were exercised. It stores equivalent logical records so export can move them into FalkorDB later. No silent fallback when a configured FalkorDB is unavailable.

`Scope` comes only from server credential lookup, with hashed random bearer tokens and explicit project/action grants. Every read, exact expansion, candidate search, traversal, graph export, event listing, and dashboard query uses that scope. Links and handoffs reject endpoints outside the permitted project; an unknown or forbidden memory returns the same 404. Retrieve permission-filtered candidates before ranking. Source content is evidence data, never executable instructions.

Initial retrieval combines indexed IDs/cues/keywords and bounded typed graph traversal, then evidence and valid-time checks. It returns compact handles with path and source IDs. `RecallStrategy` is the one replacement point for new PACE policies or a vector implementation. Keep strategy names and scores in traces so a later baseline comparison remains possible. Character budgets are strict; token counts are estimates until a tokenizer is configured. No LLM or embedding provider is mandatory.

## Module map

| Module | Owned knowledge |
|---|---|
| `models.py` | Domain records, commands, structured errors, input limits |
| `auth.py` | Credential provisioning, hashing, tenant/project/action scope |
| `memory.py` | Memory facts, source semantics, versioned writes, handoff |
| `retrieval.py` | Bounded recall strategy, ranking, handles and traces |
| `stores/falkor.py` | Graph schema, parameterized queries, atomic commit |
| `stores/sqlite.py` | Explicit local transaction and graph traversal equivalent |
| `api.py` | FastAPI boundary, HTTP errors, local dashboard routes |
| `mcp.py` | Stdio discovery/tool schemas and authenticated HTTP adaptation |
| `static/app.js` | Scoped graph facets, drill-in animation, agents, context traces |
| `cli.py` | Start service, issue scoped credentials, deterministic demo |

The UI reads graph neighborhoods and persisted activity through the same API. A project event cursor updates visible changes; active sessions use explicit heartbeat expiry, so a configured platform never appears connected without traffic. Recall traces map a query to selected nodes and paths. Facet drill-in groups sources, agents, time, and claims inside a selected episode. Reduced-motion and keyboard controls apply to every animated graph action.

## Synthesis decision

Candidate pending comparison. Retain event history even if the simpler service-oriented candidate becomes the base, because events directly support honest activity visualization and reproducible cross-agent deltas.

## Tradeoffs accepted

- Accept synchronous projections and short transactions in exchange for immediate read-after-write behavior and no background worker.
- Accept explicit agent tool calls in exchange for compatibility with hosts whose lifecycle hooks differ.
- Accept no learned PACE weights or automatic extraction in exchange for testable retrieval and source-backed writes.

## Alternatives considered

A CRUD memory service stores revisions beside each record. It has fewer concepts, but a global changes feed and activity audit must be assembled separately. Full event sourcing with asynchronous CQRS hides rebuild machinery behind commands, but makes callers handle projection lag and adds queues and recovery workers too early.

## Open questions and risks

Can the installed FalkorDB release atomically satisfy the whole guarded commit contract, including duplicate retries? Can a real Codex and Claude Code installation be exercised on this host? Until verified, label their configuration examples as provided adapters rather than tested host connections.

## Next implementation step

Build the SQLite transaction contract and test duplicate retries, competing updates, prohibited expansion, and handoff scope; run the same contract against FalkorDB before claiming that backend works.
