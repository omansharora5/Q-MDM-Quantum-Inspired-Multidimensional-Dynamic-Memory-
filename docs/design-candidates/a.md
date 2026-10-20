# Candidate A: one memory service, replaceable storage and retrieval
## Caller usage first
Custom agents use one authenticated HTTP service. MCP hosts launch a thin stdio proxy against that same service.

```python
client = MemoryClient(base_url="http://127.0.0.1:8000", token=os.environ["MNEMOGRAPH_TOKEN"])
session = client.start_session(project="qc", platform="custom-python", task="Camera decision")
packet = client.recall(project="qc", query="Why avoid complex mounting?", budget=1200)
evidence = client.expand(project="qc", memory_id=packet.handles[0].id)
receipt = client.remember(project="qc", key="run-17:decision", memory=decision)
client.update(project="qc", memory_id=receipt.memory_id,
              expected_version=1, key="run-17:revision", memory=correction)
client.handoff(project="qc", task_id="task-1", target_agent="developer",
               expected_version=2, key="run-17:handoff")
```

Codex and Claude Code configuration launches `python -m mnemograph.mcp_proxy` with service URL and token in environment variables. The proxy exposes typed `remember`, `recall`, `expand`, `update`, `handoff`, `state`, and `changes` tools. It forwards every operation through HTTP, including authentication. It cannot access storage directly.

Host instructions describe when to recall, expand evidence, and save accepted outcomes. A local or API model uses the same client in its tool loop. Tool discovery alone does not capture conversations or guarantee memory use. Provide runnable independent clients and honest host setup examples.

## Types and signatures
```python
@dataclass(frozen=True)
class Principal:
    tenant_id: str
    agent_id: str
    grants: dict[str, frozenset[str]]  # project -> read/write/coordinate

class MemoryInput(BaseModel):
    kind: Literal["episode", "fact", "decision", "procedure"]
    summary: str
    content: str
    cues: list[str]
    source: SourceInput
    links: list[LinkInput]
    valid_from: datetime | None
    valid_to: datetime | None
    verification: Literal["asserted", "source_backed"]

class RecallRequest(BaseModel):
    project: str
    query: str
    budget: int  # bounded server-side; label tokenizer estimates honestly
    as_of: datetime | None

class Handle(BaseModel):
    id: str
    summary: str
    kind: str
    version: int
    source_ids: list[str]
    path: list[PathStep]

class Packet(BaseModel):
    revision: int
    handles: list[Handle]
    trace_id: str
    truncated: bool

class MemoryService:
    def remember(self, actor: Principal, project: str, command: WriteCommand) -> Receipt: ...
    def recall(self, actor: Principal, request: RecallRequest) -> Packet: ...
    def expand(self, actor: Principal, project: str, memory_id: str) -> Evidence: ...
    def handoff(self, actor: Principal, project: str, command: HandoffCommand) -> Receipt: ...
    def state(self, actor: Principal, project: str) -> ProjectState: ...
    def changes(self, actor: Principal, project: str, after: int) -> ChangePage: ...

class Store(Protocol):
    def commit(self, scope: Scope, command: Command) -> Receipt: ...
    def get(self, scope: Scope, memory_id: str) -> Evidence: ...
    def candidates(self, scope: Scope, query: str, limit: int) -> list[Candidate]: ...
    def neighborhood(self, scope: Scope, ids: list[str], hops: int, limit: int) -> Neighborhood: ...
    def state(self, scope: Scope) -> ProjectState: ...
    def changes(self, scope: Scope, after: int, limit: int) -> ChangePage: ...

class RetrievalStrategy(Protocol):
    def recall(self, store: Store, scope: Scope, request: RecallRequest) -> Packet: ...
```

Keep business rules in `MemoryService`; transport models and signatures remain stable when retrieval changes. `Store.commit` represents the entire atomic command, never a caller-managed sequence of CRUD calls.

## Module map

| Module | Owns |
| --- | --- |
| `models.py` | Validated commands, records, receipts, bounded requests and responses |
| `auth.py` | Token digest lookup, principal, project grants, action authorization |
| `service.py` | Memory commands, source/link checks, version conflicts, project changes |
| `store.py` | Storage protocol and shared domain failures |
| `stores/falkor.py` | Parameterized graph queries, indexes, atomic command persistence |
| `stores/sqlite.py` | Explicit development adapter with identical operation contract |
| `retrieval.py` | Keyword seeds, typed bounded traversal, ranking, compact handles |
| `api.py` | FastAPI routes, auth dependency, consistent error mapping, static UI |
| `mcp_proxy.py`, `client.py` | MCP transport and small HTTP client |
| `web/index.html`, `web/app.js`, `web/style.css` | Graph, connections, context traces |
| `tests/`, `examples/`, `docs/` | Contract checks, independent clients, host setup |

## Storage, isolation, and consistency

FalkorDB is the intended authoritative graph store. A server-selected tenant graph prevents caller-controlled graph names. Every node/edge lookup also checks project, including graph neighbors, source expansion, changes, traces, and UI. Request bodies never define trusted tenant or author identity. Tokens grant only named projects and actions; bootstrap credentials live outside the repository. Bind localhost by default, constrain CORS, and never put tokens in URLs.

`commit` atomically validates expected memory/task version, writes an immutable revision plus current pointer, appends a monotonic project change, and records an idempotency receipt. The receipt key includes tenant, project, actor, and caller key. Store a canonical request hash. A matching retry returns the original receipt before checking a stale expected version; changed payload with reused key returns 409. Version conflicts return 409 and preserve the accepted value. Sources and related node IDs must exist in the same authorized project. Evidence contradictions remain separate assertions; CAS prevents lost updates but does not establish truth.

SQLite uses a write transaction and unique receipt keys for a runnable local mode. It never pretends to be FalkorDB and never becomes an unnoticed fallback after FalkorDB failure. FalkorDB must prove CAS plus revision plus receipt atomicity with concurrent requests on the deployed release before claiming this contract. One command cannot be replaced with a process-local lock that fails across workers.

## Retrieval and visual interface

Initial PACE uses exact/keyword seeds and two-hop typed traversal with hard candidate, response, and time caps. Ranking preserves evidence paths and temporal metadata. The injected strategy is one extension point for future embeddings, personalized PageRank, or a reasoning controller; no plugin framework yet. An optional strategy cannot weaken authorization. Memory content remains untrusted evidence, including procedural records.

The localhost UI queries the same scoped API. A project graph drills into episode, source, agent, time, and task facets with pan, zoom, breadcrumbs, and reduced-motion support. Poll scoped changes for observed activity. The agent panel uses authenticated sessions and `last_seen`, with explicit idle expiry. It cannot claim knowledge of all installed agents. The context panel shows recorded recall queries, selected handles, paths, revision, and expansion events. Animations follow real traces; empty data stays empty.

## Alternatives and validation

A direct embedded MCP/database package is smaller at first but duplicates auth, connection management, and write rules across independent hosts. A service plus thin proxy gives one enforced policy boundary. Microservices, queues, event buses, and separate vector stores add failure modes without a present requirement. A storage protocol is justified by the absent local Docker runtime and future algorithm work; adding more adapter interfaces is not.

Required checks cover durable restart, scoped cross-agent recall, forbidden expansion and traversal, two writers against one version, concurrent identical retries, reused-key mismatch, handoff authorization, and graph drilldown/context activity. Run shared storage contract tests against SQLite and an actual FalkorDB instance. If FalkorDB cannot run here, clearly mark its runtime verification pending.

Skipped embedding downloads, automatic LLM extraction, distributed leases, and benchmark claims. The main risk is declaring FalkorDB atomicity or live host integration before testing them.
