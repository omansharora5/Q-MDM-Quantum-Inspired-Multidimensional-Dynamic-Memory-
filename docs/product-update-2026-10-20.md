# Product update: clearer memory exploration and agent setup

The project now continues independently of the hackathon. No database vendor is
mandatory. Existing versioned memory, authorization, provenance and retry rules
remain the storage contract.

The acceptance checks for this update are:

- A person can select a memory and explain each visible connection using its
  direction, plain-language label and source/target names.
- Nodes can be dragged and their positions survive a refresh. A reset returns
  to a repeatable arrangement. A list provides the same records without dragging.
- Switching to 3D uses actual x/y/z positions and perspective projection. Orbit
  and tilt alter the projection; returning to 2D preserves the selected record.
  Visual depth describes record categories, not embedding or quantum coordinates.
- The setup guide names the local service, agent host and separate credential,
  gives complete commands, and marks success only for a matching agent heartbeat.
  A browser heartbeat alone cannot complete an agent setup.
- The supported default starts locally with SQLite. Database research separates
  Tencent's memory framework from a database engine and records migration costs.
- Source, tests, generated experiment reports and documentation are uploaded to
  the user-selected GitHub repository. Local keys/databases, virtual environments,
  imported conversation documents and scratch work are excluded.

Verification uses the real browser controls for selection, edge inspection,
node movement, 2D/3D modes, camera controls and setup feedback. A small deterministic
Node check verifies camera projection and edge geometry. The existing Python
contracts cover memory revisions, scope and retry behavior. Git's staged file
list and a local-key scan are checked before the upload; the remote commit is
read back after pushing.

The storage decision is in `storage-decision-2026-10-20.md`. The release record
must state which checks actually ran and distinguish provider configuration
examples from an exercised model session.

## Verified in this build

- Python 3.14 on Windows: 39 tests passed. The 25 optional FalkorDB server cases
  were skipped because no test server was configured. One upstream Starlette
  deprecation warning remains.
- Node geometry checks passed for depth, perspective, orbit, tilt, dragging,
  pins, trimmed directed edges and relationship names. App JavaScript syntax passed.
- The real browser opened a sourced decision, read its latest message/time,
  explained an edge by keyboard, dragged the node, and observed saved x/y/z
  placement after a page reload. Orbit and tilt changed the camera. Returning
  to 2D preserved the selected record. Arrange cleared the saved placements.
- The connection-type filter changed the selected sample from 18 arrows to four
  evidence arrows, zero conflicts, and back to 18 arrows. Pointer activation
  opened the source relationship. Filter controls also fit the 390px layout.
- Agent setup copied complete terminal steps, reported the API-only check
  separately, and completed the REST-client step only after a matching heartbeat.
  A separate Codex selection remained waiting. No model session was implied.
- At 390px, setup, graph, conversations, flow and experiments had no document
  overflow. At 768px, graph, conversations, flow and experiments had no document
  overflow. The graph and setup were also inspected at 1440px. Code blocks and
  tables retain their own horizontal scrolling. These are sampled checks, not
  a claim that every node arrangement at every viewport is collision-free.
- The actual MCP stdio subprocess exposed 14 tools and passed message, candidate,
  checkpoint, recall and evidence calls. Independent researcher/developer
  processes shared sourced memory and a handoff. The documented REST heartbeat,
  context and recall example returned successfully.

The small project snapshot design remains a scaling limit. Alternative database
runtimes, large concurrent loads and actual Codex/Claude/API model sessions were
not exercised. PostgreSQL and native graph alternatives remain researched options,
not implemented adapters. The current 3D view is an SVG perspective projection
with category depth and a movable camera, not WebGL or a neural embedding map.

![Current explorer and source relationship](assets/qmdm-explorer-2026-10-20.png)

## Publication

Code, tests, research decisions, the blog draft, plots and synthetic demo artifacts
are published in [the Q-MDM repository](https://github.com/omansharora5/Q-MDM-Quantum-Inspired-Multidimensional-Dynamic-Memory-).
The initial upload's GitHub Actions checks passed on Ubuntu and Windows with
Python 3.12 and Node 22. Local validation used Python 3.14. Private runtime
state, keys, virtual environments and imported conversation documents are excluded.
The original placeholder file was preserved. No Medium post or model-provider
configuration was published.
