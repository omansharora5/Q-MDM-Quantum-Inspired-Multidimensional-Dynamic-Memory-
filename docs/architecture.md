# Architecture and extension rules

## Caller contract

Agents connect, load a compact context snapshot, recall handles, expand relevant
evidence, then save sourced outcomes or hand off work. The model provider does
not participate in memory storage. A tool-capable local model follows the same
loop as an API-backed agent.

```text
Codex / Claude Code ─ stdio MCP bridge ─┐
Local / custom agent ─ Python / REST ──┼─ FastAPI + credential scope
Local dashboard ─ authenticated REST ─┘              │
                                              MemoryService
                                               │        │
                                       RetrievalStrategy Store
                                               │        │
                                          PACE v2    SQLite default
                                                    or optional FalkorDB
```

MCP forwards HTTP requests; it never opens the database. The dashboard uses the
same scoped API. Secrets and trusted tenant identity never come from model tool
arguments. No global agent configuration is modified by setup.

## Module ownership

| File | Owns |
|---|---|
| `auth.py` | Token digest lookup, principal scope, credential bootstrapping |
| `models.py` | Validated write/recall/handoff input and temporal intervals |
| `service.py` | Memory operations, compact startup context, evidence and handoff policy |
| `policy.py` | Private audiences, provenance closure, sharing and structured claim checks |
| `projections.py` | Logical node dimensions, exact-message mapping and revision replay |
| `retrieval.py` | Current/historical eligibility, cue traversal, ranking, bounded context |
| `store.py` | Storage contract, shared atomic preparation, SQLite transactions |
| `falkor.py` | Physical graph schema, native traversal, guarded graph commits |
| `api.py` | REST, permission dependencies, errors, headers, localhost dashboard |
| `client.py`, `mcp_server.py` | Agent access through HTTP and stdio MCP |
| `web/` | Graph, evidence, observed agents, context traces, connection templates |

## Stable data decisions

A credential binds one tenant, project, and agent to actions. Multiple agents
share the same tenant/project scope. Separate tenant or project scopes cannot
expand each other's IDs or traverse each other's relationships. The FalkorDB
graph name is a server-computed hash of tenant and project. SQLite includes that
same namespace in every primary key and query.

Each entity record includes `schema_version`, identity, kind, typed payload,
version, author, observation time, and project revision. Original source text is
data, including text that looks like instructions. The application never executes
retrieved text. Agent prompts must preserve this distinction too.

Accepted writes append immutable records and events. `expected_version` protects
an individual memory or task. A same-key/same-payload retry returns the original
receipt before testing the now-stale version. Reusing a key with different input
returns 409. The key namespace includes project scope and agent identity.

SQLite commits the record, revision, event, and receipt inside one `BEGIN
IMMEDIATE` transaction. FalkorDB performs those mutations in one guarded Cypher
write against the observed project revision. Unrelated racing commits retry
internally; competing edits to the same entity return a version conflict. The
guard's behavior still needs the real FalkorDB contract run. No process-local
lock is used as a database consistency guarantee.

CAS detects lost updates. Optional dataset-local claim keys also reject
incompatible accepted heads without explicit supersession. This is a structured
check, not natural-language contradiction detection. Disputed and superseded
records stay inspectable but are excluded from ordinary recall.

Private audiences and declared provenance links apply before retrieval and on
direct expansion, history, timeline, graph and change-feed routes. Current
permissions govern historical access. Explicit live-store forgetting redacts
linked content and historical bodies; backups and physical disk retention need
separate handling. See [the full governance contract](v2/system-spec.md).

## Retrieval boundary

`RetrievalStrategy.retrieve(state, request, adjacency=None)` returns handles,
paths, selected context, revision, and truncation metadata. Inject another
strategy into `MemoryService` to compare PACE variants without changing MCP or
REST tools. Strategies receive only the already authorized project snapshot.

PACE v2 combines BM25 and lexical TF-IDF anchors with typed links, shared cues,
bounded traversal, PPR, intent preference and a redundancy penalty. Path bundles
retain connected evidence and a small forest receipt. It allows eight seeds,
two hops and forty visited candidates. Selection fits the **serialized handle
array** into `budget_chars`; transport metadata and later evidence expansion are
outside this budget. Neural embeddings and LLM calls are not used.

The same endpoint also selects BM25, TF-IDF, bounded graph traversal, PPR or an
experimental classical continuous-time quantum-walk simulation. The wire name
`beam` denotes bounded breadth-first traversal, not score-pruned beam search.
The [measured comparison](../artifacts/benchmarks/README.md) shows no advantage
for PACE/QWAM over the simpler graph methods on the curated synthetic fixtures.

The FalkorDB adapter queries native cue and typed lifecycle relationships for current
adjacency. Historical retrieval reconstructs relationships from immutable
versions. `as_of` means knowledge recorded by that timestamp and valid at that
timestamp, so a fact first learned today does not appear in yesterday's snapshot.
It is a single-time query, not a complete bitemporal query language.

The project snapshot is currently loaded in full before ranking. The traversal
bound limits candidate expansion, not database scan cost. Native adjacency and
record snapshots are separate reads in the FalkorDB prototype and can differ
during concurrent writes. A consistent indexed candidate/neighborhood query is
needed before high-concurrency deployment.

## Add new things without coupling the clients

1. Add a new algorithm inside `retrieval.py` or another strategy module. Keep
   handles and evidence references stable. Add known-answer recall cases.
2. Add an embedding provider behind that strategy, not to the MCP tools. Version
   model name and vector dimensions; never infer dimensions from the graph UI.
3. Add a host integration by mapping its tools to the same REST operations. Give
   it a distinct scoped identity and an explicit memory-use instruction policy.
4. Add a new data field with a default and increment the record schema when the
   interpretation changes. Add an explicit migration before reading older data
   through an incompatible schema. There is no migration framework yet.
5. Add a memory kind by updating the validated model, store projection, UI type
   mapping, and contract fixtures together. Do not let model output select graph
   labels, Cypher, tenant identity, or arbitrary commands.
6. Add background extraction or consolidation only when needed. Preserve raw
   evidence and distinguish inferred claims from accepted facts.

No architecture guarantees that all future changes are conflict-free. These
boundaries keep algorithms, transports, and storage from changing together.

## Design synthesis

Candidate A is the base: one service with a deep atomic commit operation.
Candidate B contributes immutable revision/event history, which directly serves
the activity feed and changes API. Both scored 2/2 for caller simplicity,
server-derived scope, replaceable retrieval, and honest local operation. Both
scored 1/2 for atomic storage because FalkorDB behavior requires runtime evidence.
Inline comparison favored A's smaller public interface. No separate judge agent
was needed for this bounded comparison.

Rejected asynchronous projections, queues, microservices, plugin loading, and a
mandatory memory-manager LLM. They add deployment and recovery concerns before
the core memory contract needs them. Retained the two isolated candidate notes
under `docs/design-candidates/` as the decision record.
