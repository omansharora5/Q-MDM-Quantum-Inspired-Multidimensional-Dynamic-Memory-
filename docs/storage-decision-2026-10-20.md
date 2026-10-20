# Storage decision for MnemoGraph

Reviewed on 20 October 2026, Asia/Kolkata. This decision uses the current repository workload and primary project documentation. The project no longer has a hackathon requirement to use FalkorDB. No database was installed, replaced or migrated during this review.

## Recommendation

Keep SQLite as the current local authoritative store. Improve indexed candidate and edge access before changing engines. If MnemoGraph becomes a service with sustained concurrent writes, multiple application instances or operational database requirements, PostgreSQL with optional pgvector is the preferred next authoritative store. A dedicated graph engine should earn its place through a measured traversal workload. For an embedded graph experiment on this Windows machine, investigate LadybugDB rather than archived Kuzu.

Do not add a vector database and graph database merely because the product has both concepts. One transactional authority can store messages, memory versions, typed relations, permissions, tasks and embeddings. A second search engine can be a rebuildable projection if a real benchmark later justifies it.

## The likely Tencent project

The strongest match is [TencentDB Agent Memory](https://github.com/TencentCloud/TencentDB-Agent-Memory). The old `Tencent/TencentDB-Agent-Memory` address redirects there. It is an MIT-licensed memory framework and team memory hub, not a new general-purpose database engine. Its current documentation describes conversation memory, skills, a document wiki and code graphs. The inspected default branch is `feat/server_team`; the project is changing quickly. This is a likely identification, since the user did not provide the remembered link. [Repository and license](https://github.com/TencentCloud/TencentDB-Agent-Memory/blob/feat/server_team/LICENSE)

Its installation guide explicitly says the default backend is SQLite. MongoDB is experimental and disabled by default. The recommended deployment starts several containers and configures memory and model-proxy LLM endpoints. Therefore, "uses local SQLite" does not establish that every feature works without models, containers or setup. It is worth studying its integration and memory lifecycle, but adopting it is an application/framework decision, not simply swapping our database driver. [Current installation guide](https://github.com/TencentCloud/TencentDB-Agent-Memory/blob/feat/server_team/INSTALL.md)

Other names are easy to confuse:

| Name | What it actually is | Relevance here |
| --- | --- | --- |
| [Tencent Tendis](https://github.com/Tencent/Tendis) | Tencent's Redis-protocol storage system using RocksDB, GPLv3. | Self-hostable key/value infrastructure. Redis protocol compatibility does not imply Cypher or compatibility with a FalkorDB module. Poor reason to replace our transactional memory store. |
| [Tencent TBase](https://github.com/Tencent/TBase) | Distributed SQL/HTAP system based on Postgres-XL, BSD 3-Clause. | Its documented coordinator/data-node/global-transaction-manager deployment is much larger than this local workload needs. |
| [TDSQL PostgreSQL edition](https://cloud.tencent.com/product/tbase) | A Tencent product line formerly called TBase. | Do not assume every TDSQL product or cloud edition has the same source release and license as the GitHub TBase repository. |
| [Tencent Cloud VectorDB](https://www.tencentcloud.com/products/vdb) | A cloud vector-database product. | The inspected product page does not establish a public self-hostable engine release or open-source engine license. A public SDK would not establish either. |
| [Infinity](https://github.com/infiniflow/infinity) | InfiniFlow's Apache-2.0 hybrid-search database for dense/sparse vectors, tensors and full text. | It is not a Tencent project. Tensor retrieval does not mean a graph inside every node or quantum computation. |
| [Hunyuan-A13B](https://github.com/Tencent-Hunyuan/Hunyuan-A13B) | A Tencent language model. | It can help extraction or answering; it is not a database. |

## What the repository actually needs

The current `Store` contract exposes `snapshot` and `commit`; implementations also support forgetting, and the graph adapter provides adjacency. `SQLiteStore` stores current entities, revision history/events and retry receipts. It uses WAL and an immediate write transaction to run policy checks, version checks and the corresponding mutations together. Sources and typed memory links currently live in the record payload.

The main scaling problem visible in the code is that reads and writes materialize a whole scoped project snapshot, including history and receipts. Retrieval then scores text in Python and explores a bounded neighborhood. Its forty-candidate traversal cap does not cap snapshot loading or lexical indexing cost. Moving the same full-snapshot algorithm to PostgreSQL or Neo4j would keep much of that work.

The required invariants are more decisive than the graph animation:

- A memory revision, relation changes, event and idempotency receipt must commit together.
- Concurrent writes must preserve expected-version semantics.
- Authorization must apply to candidates, traversed neighbors, original messages, historical versions and direct IDs.
- Current and historical edges must remain distinguishable after a changed decision.
- Forgetting must invalidate source bodies, derivatives and search results according to policy.
- Retrieval must identify its source revision, so data and adjacency cannot silently describe different states.

These are observations and design requirements from `mnemograph/store.py`, `service.py`, `policy.py`, `projections.py` and `retrieval.py`. They are not capabilities automatically supplied by any database product.

## Practical comparison

| Choice | License and runtime | Graph/vector and consistency tradeoffs | Decision for this project |
| --- | --- | --- | --- |
| SQLite | Core is public domain; embedded and already available through Python here. | Transactions and WAL are suitable for local state. Many readers can coexist with a writer, but only one writer runs at a time. WAL requires same-host shared memory, not a network-mounted database file. FTS5 supplies lexical indexing. Graph relations can be indexed tables and traversed in SQL/application code. No neural vector index is currently configured in this project. | Keep for local development and single-service use until a measured limitation appears. [License](https://www.sqlite.org/copyright.html), [WAL](https://www.sqlite.org/wal.html), [FTS5](https://www.sqlite.org/fts5.html). |
| PostgreSQL with pgvector when needed | PostgreSQL License; pgvector uses the PostgreSQL License too. Self-hostable server with native Windows installers. | MVCC, row-level locking and transactional changes suit shared state. Edges can be relational rows, with bounded joins or recursive queries. pgvector adds exact and approximate nearest-neighbor search beside the source records. It is not a native Cypher graph engine. | Preferred service-scale target. Add pgvector only after selecting a real embedding model and demonstrating a semantic-retrieval need. [PostgreSQL license](https://www.postgresql.org/about/licence/), [MVCC](https://www.postgresql.org/docs/current/mvcc-intro.html), [recursive queries](https://www.postgresql.org/docs/current/queries-with.html), [Windows](https://www.postgresql.org/download/windows/), [pgvector](https://github.com/pgvector/pgvector). |
| Kuzu | MIT, embedded graph, but official repository archived on 10 October 2025. | Native Cypher with graph, vector and full-text features; archived maintenance is the deciding concern for new adoption. | Do not choose the archived original for a new long-lived dependency. [Official archive notice](https://github.com/kuzudb/kuzu). |
| LadybugDB | MIT embedded graph, a successor/fork of Kuzu. Official documentation includes native Windows installation. | Cypher, graph storage, full-text/vector indices and serializable ACID transactions. One read-write `Database` object must own the database; connections from it can serve concurrent requests. Transactions still allow one writer at a time. It is not a drop-in distributed multi-writer service. | Best embedded native-graph candidate to test, if Cypher traversal becomes important enough to justify an adapter. Do not promise the current Python 3.14 Windows wheel works before testing it. [Project](https://github.com/LadybugDB/ladybug), [installation](https://docs.ladybugdb.com/installation/), [concurrency](https://docs.ladybugdb.com/concurrency/), [transactions](https://docs.ladybugdb.com/cypher/transaction/). |
| Neo4j | Community Edition GPLv3; commercial editions have separate terms. Self-hostable server with native Windows installation. | Native property graph, transactional changes, Cypher and vector indexes. Vector indexes are available in Community using numeric-list properties; the newer native `VECTOR` property format requires an eligible edition/storage format. Edition and optional analytics-library terms need separate checks. | Strong graph-first server candidate when traversal complexity warrants the deployment and licensing choice. No adapter or runtime comparison has been implemented here. [Licensing](https://neo4j.com/legal-terms/), [Windows](https://neo4j.com/docs/operations-manual/current/installation/windows/), [transactions](https://neo4j.com/docs/java-reference/current/transaction-management/), [vector indexes](https://neo4j.com/docs/cypher-manual/current/indexes/search-indexes/vector-indexes/). |
| FalkorDB | Current inspected repository uses SSPLv1, distinct from permissive MIT/Apache licensing. Self-hostable server/module; the existing project deployment uses a Linux container. | Native property graphs, Cypher and sparse-matrix-based graph processing. Vector indexes are documented. Our guarded commits and consistent snapshot/adjacency behavior still require real-server verification. Current upstream and the repository's pinned image must not be assumed identical. | Optional existing adapter. Keep or remove according to verified usefulness; no event rule requires it now. [Project/license](https://github.com/FalkorDB/FalkorDB), [vector index documentation](https://falkordb.github.io/docs-staging/cypher/indexing/vector-index/). |
| Infinity | Apache-2.0, self-hostable hybrid-search engine with Python/embedded and server options. | Dense, sparse, multi-vector/tensor and text retrieval are its focus. The reviewed materials do not establish a drop-in equivalent of our multi-record CAS/receipt/provenance transaction contract or native property-graph traversal. Its documented Windows Docker path needs WSL/WSL2. | Consider as a later retrieval index, not the default source of truth. It does not remove the graph/governance work. [Project and Windows prerequisites](https://github.com/infiniflow/infinity). |

PostgreSQL itself can run natively on Windows, but installing pgvector may require a compatible package or the documented Visual Studio C++ build steps. Its approximate indexes can return fewer results under filtering; iterative scans and filter-aware index design help, but authorization cannot be treated as a similarity score. Begin with exact scoped search and measure recall before adding ANN tuning. [pgvector Windows and filtering guidance](https://github.com/pgvector/pgvector)

## Proposed architecture without a migration today

```text
Agent tools / MCP / REST
         |
Authenticated memory service
         |
One authoritative transactional store
  sources + current claims + revisions + typed edges
  audiences + tasks + leases + action receipts + retry receipts
         |
Scoped, revision-consistent candidates and neighborhood
         |
PACE / PPR / experimental CTQW in application code
         |
Evidence handles, source expansion and graph projections
```

For the current local version, that authority can remain SQLite. A later PostgreSQL implementation can use the same logical data model. Keep canonical memory IDs and typed edge rows with source/target IDs, relation, namespace, revision and validity. Represent semantic, temporal, provenance and collaboration dimensions as filtered views over these records. A dimension is not another physical database. An ego graph is a bounded query around a node.

The next useful storage change is an indexed read contract for candidates and their neighborhoods, with scope and revision carried through the whole operation. It should stop loading all history and receipts for every recall. In a PostgreSQL implementation, commit the claim, edge replacement, history, project revision and receipt in one transaction. Put uniqueness and version predicates in database writes, with appropriate locks/retries. Preserve the existing endpoint semantics rather than exposing database-specific queries to agents.

Do not introduce PostgreSQL plus a graph database plus a separate vector store as three equal authorities. If a second engine becomes necessary, feed it from committed changes, record its indexed revision, make rebuilding possible, and revalidate authorization/current versions against the authority before returning content. Deletion and permission revocation must take precedence over index freshness. This additional machinery is a reason to delay a second engine until measured search or traversal cost warrants it.

## Where the quantum-inspired experiment belongs

The repository's continuous-time quantum walk is classical NumPy computation over a bounded candidate graph. The database supplies authorized nodes, weighted edges and the revision. The application constructs a symmetric/Hermitian matrix, evolves amplitudes and ranks the resulting probabilities. No candidate database in this review is a quantum engine, and tensor/vector support does not provide quantum acceleration.

Keep this ranking behind `RetrievalStrategy`, independent of `Store`. Compare it against PPR and bounded traversal on exactly the same candidate graph, evidence budget and temporal scope. Matrix construction and numerical simulation costs belong in the benchmark. Dense eigendecomposition has growing compute/memory costs, so the candidate bound remains important. The existing synthetic experiment found no QWAM advantage over simpler graph methods; database selection should not assume one. [Existing measured report](../artifacts/benchmarks/README.md)

## When to reconsider

Measure real snapshot size, candidate-query latency, write wait time, transaction duration, recovery behavior and deletion propagation before setting a migration date. Use a recorded mixed read/write workload at the expected number of agents. Choose PostgreSQL if local write serialization or service operations become a measured constraint. Choose a native graph candidate if equivalent bounded/complex traversals demonstrably improve the workload enough to justify its operations and adapter.

Before changing the authority, export and verify current entities, every permitted historical revision, relations, sources and retry receipts. Re-run conflicts, replayed retries, privacy, forgetting, historical reconstruction, restart persistence and cross-process integration against the actual target. Switching a command-line backend flag is not a migration.

## Verification limits

The source pages above were accessible on the review date. The Tencent repository identification remains probable rather than certain without the user's original link. Kuzu's archive status, Ladybug's documented concurrency limit and the listed license identities were checked against their first-party repositories/docs. A direct FalkorDB vector-doc URL failed, so its official organization-hosted staging documentation is cited; support in the exact deployed version needs testing. Some guessed raw license URLs failed; the actual repository license links or project declarations supplied the license evidence.

No alternative engine was installed, benchmarked, crash-tested or security-audited here. Native Windows support in documentation does not establish a successful installation on this host. The previous absence of Docker/WSL is session context, not a fresh system inventory. No vendor latency or scale claim is adopted as a measured result for MnemoGraph. This document proposes a direction; it does not claim a migration has happened.
