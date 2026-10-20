# MnemoGraph submission draft

> Historical v2 material. Current product scope and database choices are in [the October 20 update](product-update-2026-10-20.md).

Track: **Agent Memory and Coordination, Track 2**

Prepared locally on 18 October; continuation reviewed on 19 October 2026. The official rules still list 18 October at 11:59 PM IST as the closing time. No extension or late acceptance was verified. This bundle is not evidence of an on-time submission.

MnemoGraph is a shared memory layer for independent agents. It keeps sourced messages, evolving claims and task state behind MCP and REST. PACE returns bounded handles and connected evidence instead of requiring every agent to replay the same conversation. The local interface shows the original message, its time, active relationships, historical revisions and observed agent activity.

The demonstration starts with a synthetic personal-assistant conversation. A travel plan changes, its active evidence links change, and a second client retrieves the revised decision. Version checks reject stale updates. Server-derived identities scope private/shared memory and direct evidence access. A separate experiment compares lexical and graph retrieval without claiming that the project beats a vendor product.

## Readiness before submission

| Capability | Current status and limit |
| --- | --- |
| Sourced memories and exact message timeline | Implemented. Sample conversations are clearly synthetic. No private host history was captured. |
| Current/history views and dynamic typed links | Implemented. A saved revision changes active links; old permitted versions remain inspectable. |
| Agent integration | REST, Python client and local stdio MCP implemented. An MCP SDK subprocess exercises transport. No actual Codex/Claude model session or ChatGPT account connection is claimed. |
| Private/shared scope and version conflicts | Implemented in service/storage policy. Re-run the contract suite before recording final evidence. Authentication is local scoped credentials, without OAuth. |
| Candidates and promotion | Asserted candidate writes and versioned promotion implemented. Automatic LLM extraction is not part of the verified workflow. |
| Coordination | Checkpoints, leases and action receipts implemented. A receipt alone cannot guarantee exactly-once effects in an unrelated external service. |
| Retrieval evaluation | 2,592 measured synthetic trials, zero runtime errors. Four benchmark tests pass. Graph methods tie; all methods have a 50% missing-fact zero-result rate. |
| FalkorDB primary runtime | Adapter implemented, actual server runtime verification blocked on this machine. SQLite development runs do not satisfy this requirement. |
| Public repository and working video | A local silent walkthrough of actual UI captures is prepared. Public source, a continuous FalkorDB demonstration and upload remain undone. |
| Hosted deployment | Not performed. Complete local setup is the intended alternative. |

The project must not be marked fully ready for the hackathon while FalkorDB runtime behavior remains unverified. The organizer requires FalkorDB to perform central product work, plus a public repository, graph-model/setup README, dependent queries or algorithms, a working video, live or complete local setup, and the entered track. The published closing time is 18 October 2026 at 11:59 PM IST. [Official rules](https://www.wemakedevs.org/hackathons/falkordb/rules)

## Reproduce the local development demonstration

From the repository root on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m mnemograph init
.\.venv\Scripts\python.exe -m mnemograph serve --backend sqlite
```

Open `http://127.0.0.1:8000` and use the local operator key from `.local/keys.json`. Keep raw keys out of the repository and video. In a second terminal:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe examples/cross_agent.py
.\.venv\Scripts\python.exe examples/check_mcp.py
.\.venv\Scripts\python.exe -m benchmarks.run
```

The process and MCP examples need the running service. They use synthetic evidence without an LLM call. The benchmark is independent of the service. Its raw JSON/CSV, runtime versions, dataset hash and charts are in `artifacts/benchmarks/`.

## Required FalkorDB validation

On a machine with a working Docker installation, follow the repository's pinned Compose configuration:

```powershell
docker compose up -d
$env:MNEMO_FALKOR_URL = 'redis://127.0.0.1:6379'
.\start.ps1 -Backend falkordb
```

Confirm `/api/health` reports FalkorDB. Run server-backed contracts with `MNEMO_TEST_FALKOR_URL` set, then repeat the actual demo and process/MCP checks against that server. Preserve restart and stale-write evidence. Do not replace this check with query-string unit tests. The graph model and queries should be reviewed alongside `mnemograph/falkor.py`, the architecture guide and the setup README.

## Submission links to fill after verification

- Public source repository: not yet supplied.
- README and graph data model: repository `README.md` and `docs/architecture.md`.
- Graph queries: `mnemograph/falkor.py`; retrieval implementation: `mnemograph/retrieval.py`.
- Local walkthrough: `artifacts/mnemograph-v2-walkthrough.mp4`, 78 seconds, silent and assembled from actual UI still captures. This is SQLite development evidence. A continuous FalkorDB demonstration and upload remain undone.
- Reproducible local setup: instructions above and the repository README.
- Experimental results: `artifacts/benchmarks/README.md`.
- Blog draft: `docs/blog-medium.md` after integration and author review.

## AI assistance disclosure

AI coding assistance contributed code, research summaries, experiment tooling and documentation drafts. The participant supplied product direction and research material. The participant must inspect the final changes, run the checks, understand the graph model and queries, and be able to explain the technical decisions. This draft does not claim those human review steps have already happened. The organizer explicitly requires disclosure and meaningful participant contribution and understanding. [Rules on AI assistance](https://www.wemakedevs.org/hackathons/falkordb/rules)
