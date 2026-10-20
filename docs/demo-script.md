# A three-minute MnemoGraph demo

> Historical v2 material. Current product scope and database choices are in [the October 20 update](product-update-2026-10-20.md).

Record the actual running result. Keep credentials out of frame. This script is a rehearsal plan for a continuous presentation. A 78-second silent walkthrough assembled from real UI still captures is available at `artifacts/mnemograph-v2-walkthrough.mp4`, with capture hashes and captions in `artifacts/walkthrough-manifest.json`. It shows SQLite development mode and synthetic data. It is not a continuous recording or FalkorDB proof. A submission-ready presentation still needs the same sequence against verified FalkorDB.

## Before recording

Start the service and authenticate the dashboard. Use a clean development workspace so the personal sample has not already been evolved; do not delete a workspace containing useful data. Keep the personal-assistant sample selected. Prepare a terminal in the repository root with the virtual environment. Run the tests first and retain their real output. The renderer must show actual saved changes and recorded activity, without fabricated connection badges.

## 0:00 to 0:25: show the conversation

Open **Conversations**, select **Personal assistant**, and generate the synthetic sample. Show Maya's vegetarian preference, train plan and rail-maintenance message. Say:

> These are synthetic messages, not a connected ChatGPT account. The backend keeps the source message and the claim derived from it separately. The latest message is visible outside the graph and from its memory node.

## 0:25 to 1:05: inspect the decision and change it

Open the graph and select **Weekend transport plan**. Open its evidence and inspect the provenance and temporal views. Use **Simulate change of plan**. Show the saved version and the new connection to **Rail maintenance changes available routes**, with the earlier evidence still available in history.

> The active plan changes from the Saturday train to the express coach. This animation follows a committed revision and a replaced evidence link. The old version is history, not another equally current plan.

Move through a source or message node's dimensions too. Explain that these are projections of canonical records; a node does not allocate another independent database. If nothing changes on a repeated click, explain that the operation reuses an idempotent receipt.

## 1:05 to 1:40: retrieve from another process

Show the **Connect an agent** guide briefly. Explain local stdio MCP versus REST and the API/local-model wrapper. In the prepared terminal, run:

```powershell
.\.venv\Scripts\python.exe examples/cross_agent.py
.\.venv\Scripts\python.exe examples/check_mcp.py
```

These existing examples use a separate synthetic camera handoff. State that distinction instead of implying their camera output came from Maya's trip. Show the actual second-process evidence check and MCP tool discovery output.

> These are independent client processes sharing the service. The MCP check uses a real stdio SDK subprocess. It opens stored evidence, but it does not call a foundation model or prove that a Codex or Claude session has been configured.

Return to **Connected agents** or **Context & handoffs** and show the newly observed activity. Do not call a configured but unused agent connected.

## 1:40 to 2:10: show a failed competing update

Show the output of these contract checks, or run them live:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_contract.py::test_same_version_writers_do_not_overwrite tests/test_contract.py::test_tenant_project_and_graph_isolation -q
```

> The competing-write check sends two updates based on the same version and confirms that one cannot silently replace the other. The isolation check exercises separate tenant/project credentials. These are automated local contract checks, not footage of two live model sessions.

For a UI version, open the same editable memory in two authenticated tabs before saving either. Save the first, then save the second stale edit. Show the 409 conflict with the second editor's text retained. Do this only after rehearsing the actual flow. Private/shared memory uses additional policy; do not describe the tenant test alone as comprehensive privacy verification.

## 2:10 to 2:45: show the measured experiment and its failure

Open **Experiments**. Show the recorded run timestamp and dataset hash, evidence recall and the missing-fact chart. If the dashboard does not expose a particular chart, open the saved PNG from `artifacts/benchmarks/`.

> There were 2,592 synthetic retrieval trials. The graph methods tie on these curated links. PACE and QWAM have no demonstrated advantage over the simpler graph baseline. Every method returns unrelated handles for known-project missing-fact queries, so the zero-result rate is only 50%. That is retrieval selectivity, not answer correctness or a model's refusal rate. The timing excludes database, network and model calls.

## 2:45 to 3:00: close with the boundary

> The working foundation is sourced, versioned memory that independent clients can inspect and update. There is no hidden access to ChatGPT history, no trained memory model and no vendor leaderboard claim. The remaining submission gate is verifying the real FalkorDB runtime, then publishing the source and an honest working video.

If FalkorDB has since passed, replace the last sentence with the actual backend name, test command and observed result. Keep AI assistance disclosure in the submission and let the participant explain the architecture in their own words.
