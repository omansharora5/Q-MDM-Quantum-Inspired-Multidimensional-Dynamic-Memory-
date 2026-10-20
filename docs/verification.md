# Verification record

## Current v2 result

Checked on 19 October 2026. `python -m pytest -q` reports **37 passed, 24 skipped**.
Every skipped case is a real FalkorDB contract variant because no server was
available. Five FalkorDB query-shape tests pass, but those do not execute Cypher
and do not prove server atomicity or compatibility. A Starlette/httpx dependency
deprecation warning remains. No test failure is hidden by it.

The added contracts cover dataset separation and idempotent seeding, actual
removed/replaced graph links, historical replay, four dimensions for every node,
private sharing and revocation across direct reads/history/graphs/traces/timeline,
source visibility closure, exact whitespace-preserving source hashes, staged
promotion, successive supersession and cycle rejection, forgetting declared derivatives without erasing another owner's original message, cursor
ownership/freshness, task fences and action retries. A changed/completed task
invalidates its old lease for a new action. Timestamp tests use different UTC
offsets to catch lexical sorting mistakes. PPR and the experimental numerical
walk conserve probability mass. The provider-neutral tool loop uses a scripted
callback test; it is not a live model evaluation.

Two independent OS client processes saved and handed off synthetic camera
knowledge, then recalled and opened its evidence. The real MCP SDK subprocess
discovered **14 tools** and exercised connect, recall, evidence expansion, exact
message ingestion, asserted candidate creation and checkpoints. Repeating both
examples after restarting the server passed with identical retry receipts.

The service OS process was stopped and restarted. All **18 memories, 11
messages, 3 tasks and 1 checkpoint** retained identical versions and bodies.
This proves the local SQLite restart case, not abrupt power-loss recovery or
FalkorDB persistence. The machine-readable summary is
[restart-v2.json](../artifacts/restart-v2.json).

### Browser checks

The running app was driven through its real controls. Personal data generation
produced ten exact synthetic messages and six derived memories. The conversation
page linked into the transport decision. Applying the change of plan displayed
six added links and five removed links, version 2, and the newer rail-maintenance
source. The version-1 node still opened the original train evidence and both
history timestamps. Its own dimensions worked. Historical nodes no longer offer
an edit action against their visual IDs.

A real independent write advanced the Spanish routine to version 2 while its
version-1 UI editor remained open. Saving the stale proposal returned 409 and
left the unsaved text in the editor. The inspector retains expanded evidence
across unchanged polling. Live recall displayed selected paths and the requested
character count; an unknown cue produced an explicit insufficient-evidence state.
Context traces showed the actual saved query. The agent view distinguished
active dashboard heartbeats from expired MCP/client heartbeats. Connection-guide
tabs showed ChatGPT, Codex, Claude Code, custom/local and REST instructions.
The experiments view matched all six saved aggregate rows, including the 50%
missing-fact zero-result rate. No application console errors were observed in
the final exercised flows; the deliberate stale save is an expected 409.

Responsive checks covered graph, conversations, guide and experiments at 375,
768 and 1440 CSS-pixel viewport settings. The final twelve cases had no document
horizontal overflow. The table and code have their own horizontal scrollers.
See [the recorded dimensions](../artifacts/ui-responsive-check.json). A faulty SVG
transform origin and narrow-screen intrinsic grid sizing were found during these
checks and fixed before the final pass. Screenshots:
[graph](assets/graph-v2.png), [memory flow](assets/flow.png),
[conversation](assets/conversation-v2.png), [stale editor](assets/conflict-v2.png),
[experiments](assets/experiments-v2.png).
Graph/conversation captures also use an isolated synthetic workspace on port
8001, avoiding changes to the user's stored data for recording.

### Graph alignment pass

A follow-up pass fixed five verified graph defects. The overview filter matched
revision-history nodes through their inherited `record.kind`, so eight
"Version 1/2" cards crowded the canvas; edges were straight center-to-center
lines crossing card interiors; the pan/zoom hint overlapped the bottom card row
at 1366×768 and 1500×950; hash navigation kept the previous scroll position and
clipped the conversation heading; and first paint styled every edge as freshly
added because the diff had no baseline. The overview now excludes revision
nodes (10 overview nodes · 16 edges for the personal-assistant dataset, with
versions still reachable in focus, the temporal dimension and the list), nodes
are laid out in type bands with the project hub centered, edges are
deterministic curves, `fitGraph()` reserves a gutter for the hint, routing
resets scroll, and first-load edges render in the default state. Before/after
captures are in `.work/ui-v2/live/`; the graph self-check and HTML/JS contract
checks now read the canonical `mnemograph/web/` files (the `.work/ui-v2/web/`
copies are retained build history) and pass.

### Explainability, onboarding and memory-flow pass

A further pass made the engine's decisions visible and the first visit
self-explanatory. Rectangular node cards became colour-coded circles with a
grouped legend (facts, preferences and how-to, episodes, agent, project,
evidence, cue); labels sit beneath each circle, hovering dims unrelated
neighbours, and edges curve between circle rims. The overview still shows 10
nodes and 16 edges for the personal-assistant dataset and was captured from 375
to 1920 CSS pixels.

Recall responses now carry a deterministic `why` per handle: the matched query
terms, the hop path with relation names, and whether the intent boost applied.
A new read-only `GET /api/extraction` explains retention per message (role, cue
overlap, change words, duplicates, superseded versions); its output states
plainly that these are computed retrospective cues over curated sample data,
not a trained classifier. The dashboard surfaces both: an explicit
retained/not-retained verdict with inline retention notes on the conversation
page, reason lines on recall handles, and a Memory flow page
that replays one real message-to-context journey — extraction verdict, stored
memory with its typed links, recalled seeds and hops, and the delivered packet
with its character budget. Opening that page performs one real recall call
against the running store (recording one context trace) and degrades to an
explanatory note if the endpoint is unavailable. Onboarding gained a three-step
agent setup card (instructions, key copy, live heartbeat detection), clarified
naming (Agents, Agent setup guide) and login copy, and an experiments intro with
advanced configuration behind a closed disclosure. The recall-strategy selector
was removed because the deployed path always uses PACE; the saved experiments
already cover the method comparison. Change-feed entries for recall traces now
read "Recall context recorded" instead of "Versioned memory change", and the
version badge is limited to memory records (an agent node had displayed a
spurious version count). A browser re-check against the restarted
local service reported no application console errors across these flows. The
new retention tests are in `tests/test_extraction.py`; browser evidence and the
re-check script are in `.work/ui-v2/live/` (`flow-final-1500.png`,
`post-restart-check.cjs`).

### Experiment and media checks

The final measured run contains **2,592 successful retrieval trials**, six
methods, three domains, three seeds, three distractor scales and two repeats.
All packets respected the shared 3,200-character budget and there were no stale
version errors. Raw rows, code/dataset hashes, summary tables and fourteen
PNG/SVG plots are in [the benchmark report](../artifacts/benchmarks/README.md).
This is a small synthetic regression experiment with curated correct links.
It is not answer accuracy, a trained-model evaluation or a competitor benchmark.
Graph methods tie, and all methods fail the known-project missing-fact case.

The 78-second [walkthrough](../artifacts/mnemograph-v2-walkthrough.mp4) is silent
and assembled from actual UI still captures. Its captions disclose SQLite and
synthetic data. FFmpeg decoded the complete output without errors. Source-frame
hashes, captions, duration and video hash are in
[the manifest](../artifacts/walkthrough-manifest.json). It is not a continuous
recording, a live hosted-model session or FalkorDB evidence. To rebuild from the
included captures, install `imageio-ffmpeg` and Pillow, then run
`python examples/render_walkthrough.py`.

### Open gates

Actual FalkorDB contracts and database restart, actual Codex/Claude/local-model
sessions, ChatGPT HTTPS/OAuth integration, answer-level source verification,
automatic extraction/consolidation (the dashboard's retention notes are
computed explanations, not a deployed extraction model) and production
load/retention remain unverified or unimplemented. A public repository, a verified FalkorDB
demonstration and upload are still needed for submission. Local source/artifact
preparation does not establish hackathon eligibility.

## Historical v1 run

The record below describes the earlier foundation, before the v2 changes above.

Run date: 18 October 2026, Asia/Calcutta.

| Claim | Evidence | Result |
|---|---|---|
| Another scoped agent can recall and expand stored evidence | Shared storage/API contract and two separate Python processes | Passed with SQLite |
| Data survives closing/reopening its store | Contract closes/reopens SQLite; a separate OS process restart retained 10 memories, 2 tasks, and 3 traces | Passed |
| Concurrent edits cannot silently overwrite | Eight writers use version 1; one succeeds and seven receive 409 | Passed with SQLite |
| Identical concurrent retries do not duplicate writes | Six requests share key/body; all receive one receipt | Passed with SQLite |
| A retry of an accepted update returns its original receipt | Repeated version-1 command after version 2 exists | Passed with SQLite |
| Reusing a key with changed input fails | Changed memory body returns 409 | Passed with SQLite |
| Tenant and project boundaries cover expansion, traversal, and links | Two forbidden scopes fail exact reads, see empty recall, and cannot link IDs | Passed with SQLite |
| Input cannot forge author identity | Extra identity field rejected; source returned only as data | Passed |
| Cues support indirect recall | Calibration episode links to camera decision through a shared hardware cue | Passed with SQLite |
| Progressive selection respects its budget | Serialized handle context stays within requested character limit | Passed |
| Disputed, expired, and future memories stay out of current recall | Time/status contract cases | Passed |
| Startup context contains current compact handles | Future accepted decision excluded; source text omitted | Passed |
| Task handoff is visible to the recipient | Writer/reader process demo and versioned task completion | Passed with SQLite |
| MCP actually transports requests | SDK subprocess discovers eight tools; calls connect, recall, expansion | Passed against running REST service |
| Dashboard uses persisted state | Browser saved a sourced record and task, then backend records inspected | Passed with SQLite |
| FalkorDB contract | Same ten tests, selected by `MNEMO_TEST_FALKOR_URL` | Skipped; no server available |

Automated result: **12 passed, 10 skipped**. The ten skipped cases are the
FalkorDB variants, not passing claims. A dependency deprecation warning from
Starlette's httpx TestClient remains; assertions and API checks passed.

Browser checks cover login, memory creation, node inspection, evidence expansion,
indirect recall, focused graph neighborhoods, graph dimensions, agents and idle
status, recall context, handoff creation/update, and integration examples. The
browser console reported no application errors during these flows.

Responsive checks at 375, 768, and 1440 CSS pixels found no horizontal overflow.
The final calibration recall highlighted three graph edges, including the
intermediate shared cue. A query with an unknown term produced the explicit
insufficient-evidence state. Final screenshot: `docs/assets/workspace.png`.
Credential CLI checks also passed for repeat initialization, distinct scoped
identity issuance, duplicate rejection, and invalid-identity rejection.

Known constraints: this does not prove a Codex or Claude model chose to use the
tools, high throughput, FalkorDB atomicity, crash recovery, or PACE superiority.
No LLM call, embedding model, competitor benchmark, or production deployment was
used. The current local dataset includes explicitly synthetic sample knowledge
and clearly named UI verification records.
