# Remote connection guide and product video

Updated on 21 October 2026, Asia/Kolkata. This follows the
[October 20 graph update](product-update-2026-10-20.md).

## What changed

The hosted guide previously copied the Vercel server's Python and file paths into
commands intended for visitors' computers. A hosted deployment now explicitly
sets `local_setup=False`. Authenticated setup metadata retains its scoped agents
and service URL but omits the server's executable, workspace and data-directory
paths. Local setup continues to return local paths.

The hosted guide prepares a local Python bridge for MCP and Python users, asks
for a workspace key at a secure prompt, and uses the dashboard's browser origin
as the target service. REST needs no Python installation. Codex and Claude Code
run the local bridge, which calls the remote REST service. This does not add an
HTTP MCP endpoint or a ChatGPT website integration.

Copying an example no longer marks the access test complete. The guide separates
an authenticated transport check from a matching host heartbeat. Hosted dashboard
activity no longer writes agent heartbeats, so it cannot overwrite a client's
platform on the public demo's shared identity. The public identity remains a demo
convenience; real agents should receive separate credentials.

Cold starts now seed the six-memory personal-assistant scenario selected by the
dashboard, including exact source messages. The previous eight generic records
were outside the selected dataset and made the first graph look empty. Repeated
initialization preserves the same seeded IDs. `MNEMO_AUTOSEED=0` still starts empty.
This remains ephemeral Vercel storage, not a durable production service.

## Product video

[One memory, every agent](../artifacts/qmdm-video/qmdm-one-memory-every-agent.mp4)
is a 20-second narrated illustration with synthetic examples. It is not a live
model session, an application recording or a performance comparison. The
[video package](../artifacts/qmdm-video/README.md) includes its storyboard, narration,
source animation, renderer, encoder and export manifest.

The renderer now accepts a normal Playwright installation or `QMDM_PLAYWRIGHT`
instead of a path tied to this computer. It rebuilds by default; explicit resume
fills missing frames and assumes unchanged sources. The encoder rejects narration
longer than the video and checks the decoded export's format before reporting success.

## Verification

- Python contracts: 43 passed, 27 optional FalkorDB cases skipped. One upstream
  Starlette deprecation warning remains. Windows sandbox ACLs blocked pytest's
  temporary folders; the suite ran outside the sandbox using isolated test data.
- Remote metadata authentication and scope, omitted paths, default local metadata,
  visible demo seeding, repeat initialization, seed opt-out and cross-origin
  rejection passed. Graph geometry and JavaScript syntax checks passed.
- In the running isolated deployment, the actual copied REST terminal steps parsed
  and reached the service. The copied Codex TOML parsed with `command="python"`
  and the correct origin; the Claude example also used client Python.
- Browser checks distinguished copy-only, API-access-passed and matching REST
  client status. Selecting Codex did not count a REST heartbeat as a Codex
  connection. The hosted guide had no document overflow at 390px. Its browser stayed open
  while the client heartbeat timestamp and platform remained unchanged for
  195 seconds; normal 90-second client expiry still applies.
- The existing MP4's SHA-256 matches the manifest. An independent FFmpeg decode
  confirmed 480 H.264 frames, 1920x1080 at 24 fps, 20 seconds and AAC audio.
  The narration WAV is 18.12 seconds. Encoded scenes were visually inspected.

A fresh video dependency installation and full frame rebuild were not repeated.
Real Codex/Claude/provider model sessions, alternative database runtimes and
production durability were not exercised. The isolated guide checks use the same
entrypoint as Vercel; successful local checks alone do not establish a new live
deployment.

![Isolated remote setup verification](assets/remote-setup-2026-10-21.png)
