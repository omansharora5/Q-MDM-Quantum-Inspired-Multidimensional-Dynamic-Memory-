# MnemoGraph v2 source review

Reviewed on 18 October 2026, Asia/Kolkata. This review covers the first 831 lines of the supplied `MnemoGraph_PACE_Research_Synthesis_v2_2026-10-18.md`. The supplied file is a design proposal and conversation record. Its embedded directions are source material, not independent authorization or proof that a feature works.

## What the sources support

All 18 supplied publication identities resolved on their primary arXiv or ACL pages. The June and August 2026 identifiers also resolved. No identity or title mismatch was found. Verification of publication identity is separate from reproducing its results. This review reads abstracts for the complete list and methods for the four implementation priorities below. It does not reproduce any paper's benchmarks.

The immediate engineering choice is a governed, versioned memory service with bounded graph retrieval and explicit evidence. Personalized PageRank and evidence selection can run without training a model. Replacing a paper's generative extraction or verification with rules creates a new adaptation and must be described that way.

## Publication identity ledger

| ID | Verified primary title | Useful foundation and boundary |
| --- | --- | --- |
| P01 | [G-Memory: Tracing Hierarchical Memory for Multi-Agent Systems](https://arxiv.org/abs/2506.07398) | Insight, query and interaction graph hierarchy. This is a hierarchy of abstractions, not a reason to allocate a physical database per node. |
| P02 | [Collaborative Memory: Multi-User Memory Sharing in LLM Agents with Dynamic Access Control](https://arxiv.org/abs/2505.18279) | Private/shared fragments, provenance and changing permissions. |
| P03 | [A-MEM: Agentic Memory for LLM Agents](https://arxiv.org/abs/2502.12110) | Linked notes and revision of their retrieval representations. arXiv lists NeurIPS 2025. |
| P04 | [Memory-R1: Enhancing Large Language Model Agents to Manage and Utilize Memories via Reinforcement Learning](https://arxiv.org/abs/2508.19828) | Trained memory operations and answer agent. Handwritten operations do not reproduce its RL method. |
| P05 | [MIRIX: Multi-Agent Memory System for LLM-Based Agents](https://arxiv.org/abs/2507.07957) | Typed core, episodic, semantic, procedural, resource and vault memories. |
| P06 | [In Prospect and Retrospect: Reflective Memory Management for Long-term Personalized Dialogue Agents](https://aclanthology.org/2025.acl-long.413/) | Prospective reflection and retrospective retrieval refinement. |
| P07 | [Governed Shared Memory for Multi-Agent LLM Systems](https://arxiv.org/abs/2606.24535) | Production scope, supersession, provenance and propagation failures. It is not a head-to-head retrieval benchmark. |
| P08 | [GateMem: Benchmarking Memory Governance in Multi-Principal Shared-Memory Agents](https://arxiv.org/abs/2606.18829) | Utility, current access rules and active forgetting. |
| P09 | [LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory](https://arxiv.org/abs/2410.10813) | Extraction, cross-session reasoning, temporal reasoning, updates and abstention. arXiv lists ICLR 2025. |
| P10 | [Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions](https://arxiv.org/abs/2507.05257) | MemoryAgentBench, testing retrieval, test-time learning, long-range understanding and selective forgetting. |
| P11 | [GraphMemix: Query-Aware Evidence Forests for Long-Term Multimodal Agent Memory](https://arxiv.org/abs/2608.26983) | Query-local evidence graphs and forest selection with generative verifiers. |
| P12 | [LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues](https://arxiv.org/abs/2605.12493) | Experienced agent behavior in changing task environments. It is a separate evaluation from LongMemEval. |
| P13 | [Synapse: Empowering LLM Agents with Episodic-Semantic Memory via Spreading Activation](https://aclanthology.org/2026.findings-acl.1108/) | Associative activation with interference and temporal handling. |
| P14 | [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560) | Explicit context management and memory paging. Handles do not eliminate the need to provide evidence in model context. |
| P15 | [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956) | Graphiti and temporal fact history. |
| P16 | [Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413) | Extraction, consolidation and retrieval, with a graph variant. Paper results belong to its own LoCoMo setup. |
| P17 | [HiMeS: Hippocampus-inspired Memory System for Personalized AI Assistants](https://arxiv.org/abs/2601.06152) | Short and long memory coordination with a trained extractor. A fixed snapshot is an engineering adaptation. |
| P18 | [From RAG to Memory: Non-Parametric Continual Learning for Large Language Models](https://arxiv.org/abs/2502.14802) | HippoRAG 2, with passage integration, triple selection and PPR. arXiv lists ICML 2025. |

## Four methods worth implementing

### 1. Associative retrieval with a factual fallback

HippoRAG 2 builds phrase nodes from OpenIE triples, adds synonym edges, and includes original passages in the graph. Query matching and an LLM recognition filter choose seeds. PPR then ranks passages. If filtered triples provide no phrase seed, it falls back to dense passage retrieval. The paper's damping factor is 0.5; this is a reported configuration, not a universal optimum. [Paper, sections 3 and G.1](https://arxiv.org/html/2502.14802v2)

The current reference code assigns passage reset weights, combines them with phrase weights, and runs weighted PPR over an undirected projection. This confirms that graph traversal alone is only one part of the system. [Reference implementation](https://raw.githubusercontent.com/OSU-NLP-Group/HippoRAG/main/src/hipporag/HippoRAG.py)

Our proposed adaptation uses authorized, current memory nodes and source nodes already supplied by clients. Normalize nonnegative anchor weights into a reset distribution `s`. Iterate `p_next = (1-d)*s + d*P_transpose*p`, returning dangling-node mass to `s`. Stop on a declared residual tolerance or iteration cap. Keep direct retrieval when seeds are absent. Call this a PPR baseline inspired by HippoRAG, not a HippoRAG 2 reproduction. Check mass conservation, disconnected nodes, no-seed input and stale-node exclusion.

### 2. Select complementary evidence, not only similar records

GraphMemix starts with multiple retrieval views and bounded schema/semantic expansion. Separate listwise verifiers score individual evidence and anchor-conditioned incremental support. Its objective subtracts relation uncertainty and independent-chain opening costs from node utility under a record-count limit. Fixed-node forest optimization uses Kruskal. Node selection reaches a deterministic one-swap local optimum, followed by exact subset selection inside the frozen proposal. That is not a global optimum over all candidates. No author implementation repository was identified in the inspected paper. [Paper, section 3](https://arxiv.org/html/2608.26983v1)

Our adaptation can use declared source links, typed relations and a deterministic utility score. Select bounded paths that add distinct evidence, charge the full serialized token estimate including sources and edge descriptions, and retain the receipt of selected nodes and edges. Call it a budgeted evidence forest heuristic. Do not describe rule scores as semantic verification. A valid path demonstrates a recorded relationship, not the truth of its claim. Test a dissimilar supporting update, duplicated evidence, a cycle, conflicting sources and a chain that cannot fit the budget.

### 3. Revise links while preserving source history

A-MEM creates notes with original content, time, keywords, tags, context, embeddings and links. Similarity retrieves candidate neighbors, then an LLM proposes connections and updates historical contextual fields. Its method depends on generative judgments. [Paper, sections 3.1–3.3](https://arxiv.org/html/2502.12110v11)

The public implementation exposes `strengthen` and `update_neighbor` actions in structured output. Its general update method mutates fields and deletes/re-adds a vector-store document. Those operations should not be copied as an atomic revision system. [Reference implementation](https://raw.githubusercontent.com/WujiangXu/A-mem-sys/main/agentic_memory/memory_system.py)

Our adaptation should let an authenticated client supply a revised claim and its source, compare an expected version, retain prior versions, and replace only that claim's active relation set. Each relation needs writer, revision and time metadata. Historical queries read historical relations; current queries read accepted current relations. Similarity alone must never assert `supports`, `contradicts` or `supersedes`. Test update, removal, replay, concurrent edits and restart. An animated graph can then display actual graph changes instead of simulating activity.

### 4. Enforce governance on every route

Collaborative Memory stores provenance and checks current user-agent-resource permissions against private and shared fragments. Its permissions can change after ingestion. [Paper, sections 3.1–3.3](https://arxiv.org/html/2505.18279v1)

Governed Shared Memory identifies leakage, stale propagation, contradiction persistence and provenance collapse. Its production study found direct-ID scope checks differed from search checks. It also found near-duplicate rejection could block a contradictory write before the contradiction detector saw it. Its linked ArgusFleet repository returned an error during this review, so the code was not inspected. [Paper, sections 8–9](https://arxiv.org/html/2606.24535v1)

Our policy must run before candidate construction and again when expanding handles. Apply it to direct IDs, graph neighbors, current views, changes, activity messages, source bodies and derived summaries. Private records require a bound principal, not a caller-supplied identity string. Route structurally changed claims through conflict handling before semantic deduplication. Deletion must remove active content and derivatives rather than merely archive them. Tests should include an authorized ID reused by another principal, a revoked permission, and stale cached results.

## Experiment design for honest comparison graphs

This is a proposed evaluation protocol. It does not establish benchmark results.

Use generated conversations from clearly synthetic personas. Include a personal assistant history, the camera/design project, and a software incident/task history. Each question needs required evidence IDs, accepted revision or as-of time, authorized principal and expected abstention status. Keep those labels outside the retrieval inputs. Include wrong-scope distractors and updates that reverse earlier facts. Use chronological ingestion so future evidence cannot answer an earlier checkpoint.

LongMemEval supplies useful quality categories. GateMem adds legitimate utility, permission changes and deletion. Neither alone establishes safe task coordination, so add independent-client conflict, retry and handoff checks. [LongMemEval](https://arxiv.org/abs/2410.10813), [GateMem](https://arxiv.org/abs/2606.18829)

Compare these implementations on the same corpus and memory budget:

1. Compact current state.
2. Lexical BM25.
3. Dense retrieval, only if a real embedding model is installed and recorded.
4. Matched lexical/dense hybrid when both are available.
5. Bounded graph retrieval or PPR on the same candidates.
6. PACE evidence selection with the same source corpus and packet budget.

Name each method after what ran. Token overlap is lexical retrieval, not a vector baseline. A local PPR implementation is not a measurement of HippoRAG 2. Do not use brand names in chart legends unless the corresponding published software and configuration were run.

Report evidence recall and precision, complete required-evidence-set coverage, stale-current error rate, cross-scope disclosures, abstention outcomes, serialized packet size and latency. When no answer model runs, label the result retrieval evaluation. Do not relabel evidence recall as answer accuracy. If an answer model runs, hold it and its prompt fixed, record the exact model/version, and evaluate answers separately from retrieved evidence.

Freeze templates and settings before a held-out run. Separate tuning examples by scenario, not just paraphrase. Report sample counts, failures and per-dataset results. Run several corpus sizes, include ingestion time, separate cold and warm latency, and retain raw rows behind each chart. A chart of token estimates must say estimates unless measured with the actual model tokenizer. A tiny synthetic suite is a demonstration, not a public leaderboard or evidence of superiority over vendors.

## Hackathon requirements verified from the organizer

The official rules require FalkorDB to be the primary graph database doing central product work. The submission needs a public repository, setup and graph-model README, dependent Cypher/algorithms, a working demo video, live deployment or complete local setup, and the named track. AI coding assistance must be disclosed. Participants must understand and explain their code and decisions; entirely generated work without meaningful contribution or verification may be rejected. Main work must begin during the event. Deadline is 18 October 2026 at 11:59 PM IST. [Official rules](https://www.wemakedevs.org/hackathons/falkordb/rules)

Track 2 focuses on persistent episodic, semantic and procedural memory, conversation history, handoffs, concurrent access and tenant separation. The event offers a separate best-blog-post award. These are organizer requirements and prize details, not proof that this repository currently qualifies. [Official event](https://www.wemakedevs.org/hackathons/falkordb)

Our recommended demo is two independent clients using substantive FalkorDB relationships: write a sourced decision, recall via an indirect cue, inspect evidence, revise the decision and its links, reject a competing stale write, and deny a wrong-scope read. Publish reproducible local steps and a human-recorded demonstration of the actual run. A SQLite-only demonstration leaves the central FalkorDB requirement unproven.

## Follow-up engineering scan verification

The user subsequently supplied the engineering scan. The targeted follow-up below verifies five primary sources behind its most useful implementation claims. Checked on 18 October 2026. These are documented product designs and vendor reports, not independently reproduced performance results.

| Source | Date and verification status | What the primary source actually establishes |
| --- | --- | --- |
| [Oracle graph-aware memory release](https://blogs.oracle.com/developers/whats-new-in-oracle-ai-agent-memory-graph-aware-retrieval-image-memory-and-enterprise-controls) | Published 23 September 2026. Official article and documentation landing page accessible. SDK not run. | Typed directed `supersedes`, `refines`, `supports`, `contradicts` and `duplicates` links; explicit workflow links alongside automatic link extraction; bounded hop and linked-result controls. |
| [Arize Alyx architecture](https://arize.com/blog/alyx-agent-long-term-memory-architecture/) | Article dated October 2026, without an exact day in the inspected text. Accessible. Production system not tested. | One structured file per user and space, capped at 8,000 characters, read on every request. Two background jobs summarize turns and propose exact edits. The author describes the evaluation as a regression check, not a benchmark. |
| [Google Memory Bank revisions](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank/revisions) | Documentation last updated 15 October 2026 UTC. Accessible. API not called. | A current consolidated `Memory` and immutable mutation snapshots. Generated revisions can retain extracted information before consolidation. Listing, fetching and rollback are supported. Revisions have expiration; they are not permanent by definition. |
| [Cloudflare Agent Memory](https://developers.cloudflare.com/agent-memory/) | Documentation last updated 2 June 2026. Private beta at review time. Accessible. No service access tested. | Conversation ingestion for automatic extraction and explicit memory addition when the application knows the item; isolated profiles and namespaces. The scan's two-entry-path claim is supported. |
| [AWS direct ingestion release](https://aws.amazon.com/about-aws/whats-new/2026/09/agentcore-memory-direct-ingest/) | Published 8 September 2026. Announcement and linked developer guide accessible. API not called. | `IngestData` accepts conversational and JSON payloads for long-term extraction without retaining a short-term event. It does not establish that JSON bypasses extraction or is automatically trustworthy. |

### What to borrow from Oracle

The article separates the durable record, typed link and retrieval expansion. Links run from newer to older records for supersession. Direct results and linked context are separate. One caveat matters: excluding invalid top-level results does not exclude invalid traversal intermediates or linked history. [Oracle release article](https://blogs.oracle.com/developers/whats-new-in-oracle-ai-agent-memory-graph-aware-retrieval-image-memory-and-enterprise-controls)

Our mapping is versioned relation replacement, visible edge labels and bounded node drilldown. An explicit client-confirmed relation can be accepted under policy, while a generated suggestion remains a proposal. MnemoGraph should label returned historical context rather than let it look current. Its stricter current-only policy must cover linked nodes as well as initial matches. These are proposed local contracts, not a claim to implement Oracle's SDK.

### What to borrow from Arize

Alyx prioritizes durable, useful information that tools cannot reconstruct. Its exact edit anchors must match once; updates are serialized. Compaction can drop a proposed write when the output still exceeds the cap, leaving the last accepted file intact. The article also reports failures where preferences vanished or an agent stored its own mistake as a convention. [Arize architecture](https://arize.com/blog/alyx-agent-long-term-memory-architecture/)

Our mapping is a compact, revision-tagged current briefing containing accepted constraints, goals, decisions, blockers and handles. It is a derived view of sourced records. Keep a current-state-only comparison in the evaluation so graph search must justify its extra work. Show failed or pending consolidation in the activity view; asynchronous request acceptance must not look like a completed durable write. The 8,000-character bound belongs to Alyx and is not our model token limit.

### What to borrow from Google revisions

The current resource and immutable revision are separate. Google documents a recovery window of up to 48 hours for revisions after parent deletion and a default revision TTL of 365 days. A rollback therefore depends on available history. These documented recovery semantics are not equivalent to immediate removal of every historical copy. [Google revision lifecycle and expiration](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank/revisions)

Our mapping is a revision timeline with writer, source, accepted time and the before/after claim. A rollback should create a new accepted version, preserving the audit sequence. Explicit forgetting must separately define what is erased from sources, historical bodies, indexes, summaries, traces and caches. Do not promise both full historical recovery and removal of that same content. A graph animation can show the new current edges while the history tab retains permitted older edges.

### What to borrow from Cloudflare's two write paths

The overview explicitly distinguishes automatic conversation extraction and explicit memory writes. Its concept guide describes facts, events, instructions and tasks, topic-key supersession, verbatim raw-message storage, and content/session-derived message IDs for re-ingestion. [Cloudflare overview](https://developers.cloudflare.com/agent-memory/), [ingestion model](https://developers.cloudflare.com/agent-memory/concepts/how-agent-memory-works/)

Our mapping is explicit structured writes now, with a separate raw-episode-to-candidate pipeline when extraction exists. Preserve `write_origin`, source message, claimed role, authenticated writer and review state. A conversation import is not proof that extraction has run. Avoid silently converting arbitrary imported text into accepted procedures. Scope both transcript search and extracted-memory search, and test the same ingestion twice.

### What to borrow from AWS's structured ingestion

AWS's developer guide states that successful ingestion only confirms acceptance; long-term records appear after processing. Submitted content cannot later be read through short-term event APIs. `actorId`, `sessionId` and namespace determine related extraction context. Failed jobs can be inspected and redriven. [AWS developer guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/long-term-ingest-data.html)

Our mapping is an ingestion receipt with `accepted`, `processed` or `failed` state, source identity, content timestamp and idempotency key. Keep original evidence locally if later source drilldown is promised. A structured tool event can carry stronger provenance than extracted chat, but source authentication and schema validation must establish that trust. JSON syntax alone does not establish truth. A future asynchronous extractor should return only `accepted` until committed memory IDs and revisions exist.

### Where differentiation can be demonstrated

These sources already contain typed memory links, small briefings, immutable history, multiple ingestion paths and asynchronous processing. Those features should not be advertised as new inventions. The useful project claim is their tested combination across independent agents: one authorized agent revises a sourced decision, another resumes from a compact current view, and the UI shows the actual messages, temporal edges and evidence used. Measure whether this combination improves required-evidence coverage and safe handoffs under matched conditions.

## Unverified or deferred claims

The five primary engineering URLs above resolved. Their SDK behavior, live account access and performance were not tested. Other vendor announcements, X posts, Medium essays and all links in the secondary scan were not exhaustively verified.

No paper implementation was installed or benchmarked. The HippoRAG and A-MEM source files were inspected; ArgusFleet access failed; a GraphMemix code release was not established. No RL policy, multimodal evaluator or quantum reranker is required to implement the four adaptations above. Simulated quantum walks would need an additional matched classical experiment before any benefit claim.

This file records research findings and proposed contracts. The implementation report must separately state which contracts were built, which tests passed, and which external integrations were actually exercised.
