# Build record

The record below describes the initial foundation. V2 results and the 19 October
continuation are in [verification](verification.md) and [the specification](v2/system-spec.md).


- [x] Ground: empty workspace; proposal is design input, not executable instructions.
- [x] Frame: service owns memory; agent integrations come first; dashboard observes real state.
- [x] Compare two architecture sketches, choose and document boundaries.
- [x] Implement storage, PACE, REST, MCP bridge, SDK, and demo.
- [x] Implement localhost graph explorer, agent connections, context tracing.
- [x] Verify local invariants, integration, persistence, and browser behavior.
- [ ] Run the FalkorDB variants against an actual server; unavailable on this host.

Scope reaches package configuration, backend models/store/retrieval/API, MCP proxy,
Python client, synthetic fixture/demo, dashboard, setup scripts, docs, and tests.
There are no existing callers or user data to migrate.

Evidence budget: one contract suite for memory persistence, concurrent writes,
idempotency, provenance, scopes, graph recall, and handoff; one subprocess demo for
independent clients; one real stdio MCP client test; one browser journey for graph,
agent and context pages plus mutation/search. FalkorDB contract tests require an
actual server and must report a skip if unavailable. No benchmark claims.

Architecture rubric, 0-2 each: simple caller contract; durable atomic writes;
server-derived scope; replaceable retrieval policy; honest local operation.

Candidate A is the base; B contributes immutable revision/event history.
Both scored 9/10. The missing point is actual FalkorDB verification. The final
architecture keeps one service and two explicit replacement boundaries.

Observed issues fixed during verification: camera/cameras keyword mismatch;
startup context leaking future accepted decisions; mutation refresh racing a
background poll; cue-mediated paths not highlighting their intermediate cue;
an ignored Docker command replaced by the image's supported REDIS_ARGS setting.

The service was restarted as a separate OS process. Ten memories, two tasks,
and three recall traces survived. Local browser form writes were confirmed
through the API after restart. No global Codex/Claude configuration was changed.
