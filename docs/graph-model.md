# Graph model and key queries

The physical graph contains `Project`, `Entity`, `Agent`, `Revision`, `Event`,
`WriteReceipt`, `Source`, and `Cue` labels. `Entity.kind` distinguishes memory,
task, heartbeat, trace, exact message, checkpoint, lease, action and expansion
activity; `Entity.record` preserves the versioned payload. The validated payload
has eight memory types, dataset, source trust and visibility. Current policy
checks run on canonical records before graph projection reaches a caller.

```text
(Entity)-[:ABOUT]->(Project)<-[:WORKS_ON]-(Agent)
(Entity)-[:AUTHORED_BY]->(Agent)
(Entity)-[:HAS_CUE]->(Cue)<-[:HAS_CUE]-(Entity)
(Entity)-[:RELATED_TO]->(Entity)
(memory:Entity)-[:SUPPORTS|SUPERSEDES|CONTRADICTS|REFINES|DUPLICATES|DERIVED_FROM]->(memory:Entity)
(memory:Entity)-[:SOURCED_FROM]->(message:Entity)
(WriteReceipt)-[:RECORDED]->(Revision)-[:CHANGED]->(Entity)
(Revision)-[:EVIDENCED_BY]->(Source)
(task:Entity)-[:ASSIGNED_TO]->(Agent)
```

Sources belong to immutable revisions. Updating a memory replaces its current
cue and explicit relationship projection while retaining historical evidence.
JSON records keep the initial schema small; indexed properties and more specific
labels can be promoted when query performance requires them.

Current cue-based association, used by the FalkorDB adapter:

```cypher
MATCH (a:Entity)-[:HAS_CUE]->(c:Cue)<-[:HAS_CUE]-(b:Entity)
WHERE a.id <> b.id
RETURN a.id, b.id, 'cue:' + c.name
```

Explicit neighborhood:

```cypher
MATCH (a:Entity)-[:RELATED_TO]-(b:Entity)
RETURN a.id, b.id, 'RELATED_TO'
```

Commit guard, followed in the **same query** by entity, revision, event, source,
and receipt mutations:

```cypher
MATCH (p:Project {id:'project'})
WHERE p.revision = $base
SET p.revision = $revision
MERGE (n:Entity {id:$id})
SET n.record = $record
RETURN n.id
```

The complete query lives in `mnemograph/falkor.py`. Values are client parameters;
the service selects graph names and relationship types. A no-row result retries
from the latest snapshot, including its idempotency receipts.

The dashboard groups this physical model into knowledge, provenance, and
coordination dimensions, plus a temporal view. Every projected node has its own
bounded neighborhood for those four views. An evidence child and its revision
are distinct concepts; visual dimensions do not change database or embedding
dimensions. Historical graph replay reconstructs earlier heads from permitted
revision records. Native current links do not themselves hold the whole history.

The relationship alternatives in the schema sketch above are notation. The
adapter writes a single allowlisted relationship type per link. Client text
cannot choose arbitrary Cypher. Updating a memory replaces its active typed,
cue and source-message links. Explicit forgetting also redacts linked revision
bodies and sources, removes affected relationships and retains tombstones.
These FalkorDB mutations have query-shape checks; actual execution remains
unverified until the [runtime contract](falkordb-runtime.md) passes.

Official reference: [FalkorDB Python client](https://github.com/FalkorDB/falkordb-py).
The pinned image configuration follows the [v6.0.2 runtime entrypoint](https://github.com/FalkorDB/FalkorDB/blob/v6.0.2/build/runtime/run.sh).
