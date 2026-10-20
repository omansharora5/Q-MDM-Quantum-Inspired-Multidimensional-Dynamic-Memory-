# FalkorDB runtime verification

> Historical v2 material. Current product scope and database choices are in [the October 20 update](product-update-2026-10-20.md).

Checked on this Windows host on 18 October 2026. **FalkorDB runtime verification is blocked by the missing container runtime.** SQLite results do not verify the FalkorDB adapter.

## What was observed

- No `docker`, `podman`, or `redis-server` executable was found on PATH.
- Docker Desktop, Podman, Rancher Desktop, and QEMU were absent from the checked machine and per-user installation locations.
- No Docker, Podman, WSL, or Redis service or process was found, and port 6379 had no listening TCP service.
- Windows provides `wsl.exe`, but `wsl --list --verbose` exited with code 1 and installation usage. No WSL distribution registry entry was found. This is not a working Linux runtime.
- No project FalkorDB URL or container host environment setting was configured. Secret files and unrelated account credentials were not searched.

No OS features, global settings, or external accounts were changed. The container commands below are a reproducible verification plan, not a record of a successful run.

## Supported ways to remove the blocker

The [official FalkorDB quick start](https://docs.falkordb.com/) offers Docker or a managed cloud instance. On this host, use Docker Desktop with Linux containers after completing the [official Windows prerequisites](https://docs.docker.com/desktop/setup/install/windows-install/). The WSL backend requires a working WSL installation. Microsoft documents that installation in its [WSL guide](https://learn.microsoft.com/en-us/windows/wsl/install).

Alternatively, use an existing Linux host or an existing dedicated FalkorDB instance whose URL the operator supplies. This investigation did not create a cloud account. A normal Redis server without the graph module is insufficient.

## Isolated contract run

Use a dedicated container on port 16379 so tests never share the application's Compose database or volume. The image matches the project's pinned [FalkorDB v6.0.2 release](https://github.com/FalkorDB/FalkorDB/releases/tag/v6.0.2). If the container name already exists, inspect it and restart that test container, or choose a fresh name and volume. Do not remove an existing container to resolve a name collision.

Run from PowerShell after Docker Desktop is running:

```powershell
cd 'D:\agent memory'
docker version
docker run --detach --name mnemograph-falkor-contract --publish 127.0.0.1:16379:6379 --mount type=volume,source=mnemograph-falkor-contract-data,target=/var/lib/falkordb/data --env 'REDIS_ARGS=--appendonly yes --appendfsync everysec' falkordb/falkordb:v6.0.2
docker exec mnemograph-falkor-contract redis-cli ping
docker exec mnemograph-falkor-contract redis-cli GRAPH.LIST
docker exec mnemograph-falkor-contract redis-cli CONFIG GET dir
```

Wait for `PONG`, a successful graph command, and a data directory inside the mounted path. If startup is still in progress, inspect `docker logs mnemograph-falkor-contract` and repeat the checks. A successful `PING` alone does not prove graph support. The release's [runtime Dockerfile](https://github.com/FalkorDB/FalkorDB/blob/v6.0.2/build/runtime/Dockerfile) sets `/var/lib/falkordb/data` and provides `/data` as an alias. The [Docker operations guide](https://docs.falkordb.com/operations/docker) documents persistence and `REDIS_ARGS`.

```powershell
$taskPreviousFalkorUrl = $env:MNEMO_TEST_FALKOR_URL
try {
    $env:MNEMO_TEST_FALKOR_URL = 'redis://127.0.0.1:16379'
    .\.venv\Scripts\python.exe -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'FalkorDB contract verification failed' }
} finally {
    $env:MNEMO_TEST_FALKOR_URL = $taskPreviousFalkorUrl
}
```

The parametrized contract exercises both SQLite and FalkorDB, including concurrent updates, idempotent writes, tenant/project isolation, relationship recall, history, and handoffs. Confirm that FalkorDB cases actually ran rather than being skipped. Tests retain graphs with randomized project names for inspection.

## Restart proof

The contract suite opens a new application instance, which is different from restarting the database. Check the latter separately on the dedicated test container:

```powershell
docker exec mnemograph-falkor-contract redis-cli GRAPH.QUERY mnemo_runtime_probe "MERGE (n:Probe {id:'restart-check'}) RETURN n.id"
docker exec mnemograph-falkor-contract redis-cli SAVE
docker restart mnemograph-falkor-contract
docker exec mnemograph-falkor-contract redis-cli GRAPH.QUERY mnemo_runtime_probe "MATCH (n:Probe {id:'restart-check'}) RETURN n.id"
```

The final query must return `restart-check` after the server is ready. Record the image digest, test counts, and observed query result before claiming FalkorDB support was verified. Graceful restart plus `SAVE` does not establish crash durability or the concurrency guarantees of the graph write query.

Stop with `docker stop mnemograph-falkor-contract`. The test data remains in its separate named volume. Application Compose startup remains `docker compose up -d`; it uses port 6379 and its own `graph-data` volume. Never use volume deletion as a restart step.

## Current limit

The adapter and Compose configuration have not been executed against FalkorDB on this host. Native Cypher behavior, concurrent revision guards, database restart persistence, and crash recovery therefore remain unverified. No adapter changes were made based only on a guessed query failure.

The v2 adapter now projects typed memory relationships and message origins, replaces links during updates, and constructs a guarded forget query covering entity bodies, historical revision bodies, source nodes, affected relationships, and orphaned cues. `tests/test_falkor_queries.py` captures generated queries and checks parameterization, the relation allowlist, redaction coverage, and idempotent retries. These checks cannot establish Cypher execution, locking, or persistence. The real contract run must still verify those claims, including inspection that forgotten content is absent from native graph storage.
