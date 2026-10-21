# Local-first memory integration feasibility

Research checked on 21 October 2026 against the official sources linked below. This note describes platform capabilities and proposed Q-MDM work. It does not establish that Q-MDM has shipped a browser extension, native messaging host, desktop installer, or automatic prompt hook.

## What is feasible

Q-MDM can keep its memory database and retrieval process on the user's computer. An integration can retrieve relevant memory before a model sees a prompt, then include a bounded context block. The integration method depends on the host. A Claude Code hook is an official way to add context automatically; a browser extension can modify a supported site's composer through its DOM. Those are different integration contracts, with different reliability. [Claude Code hooks](https://code.claude.com/docs/en/hooks), [Chrome content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts).

This does not demonstrate a way to replace a provider's internal memory or private system prompt. Injected context joins whatever other context the provider assembles. Product wording should say "shared memory supplied before supported prompts" and identify the supported integrations. It should not promise to bypass or disable ChatGPT or Claude memory.

Local memory storage also does not make a cloud conversation local. Memory placed in a ChatGPT or Claude prompt becomes part of the information submitted to that provider. A fully local workflow needs both local memory and a local model. This is an architectural consequence of sending that augmented prompt, not a new browser capability.

## What "layering memory" means

There are three different things to keep separate:

1. Model weights contain learned knowledge. Q-MDM does not alter them.
2. The host assembles a conversation, instructions, tools and any native memory.
3. Q-MDM retrieves selected personal/project evidence and supplies it as additional context.

Do not assume every GPT or agent automatically has persistent personal memory.
For example, OpenAI documents stateless generation requests and explicit ways to
carry conversation state across calls. A hosted chat application's memory is a
separate product feature. [OpenAI conversation state](https://developers.openai.com/api/docs/guides/conversation-state).

Our proposed context assembly is a small current brief plus question-relevant
evidence, including source IDs, versions and observation times. Raw transcripts
remain in local storage and are searched when needed. Avoid sending the entire
graph on each turn. If evidence conflicts with the current prompt, preserve the
conflict and ask for clarification where it matters; an older preference should
not silently override a new instruction. Retrieval before submission guarantees
an attempted lookup, not that the model follows or correctly cites the result.

## OpenAI platform findings

| Integration | Verified platform support | Q-MDM decision |
|---|---|---|
| Codex local runtime | `UserPromptSubmit` receives the pending prompt and can add context before processing. Non-managed hook definitions require trust review. | Build a host-specific hook adapter around local retrieval. Test the installed client version and hook trust before marking it active. [Hooks](https://learn.chatgpt.com/docs/hooks). |
| Manually installed Codex plugins | Plugins can bundle lifecycle hooks, but hook-containing plugins are not currently eligible for the public plugin directory. | A manual developer installation is a viable first distribution route; do not promise directory publication for the same hook package. [Plugin packaging](https://developers.openai.com/plugins/build/plugins). |
| ChatGPT custom MCP connection | Secure MCP Tunnel can connect a private stdio or HTTP server through an outbound client. It needs a tunnel identity, runtime API key and relevant Platform/workspace permissions; public plugin distribution uses a different path. | Optional integration for eligible users, not the default consumer installation. The database can remain local, but selected tool results pass through OpenAI. This route is not configured in Q-MDM. [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels). |
| ChatGPT desktop-only plugin directory | Official local MCP submission exists, but is limited to approved partners. | Investigate eligibility separately. Do not make the desktop/browser release depend on partner approval. [Desktop-only submissions](https://developers.openai.com/plugins/deploy/desktop-only). |

These are distinct from offering a memory tool and hoping it gets called. The
MCP guide describes model-selected tool use. It does not establish a universal
pre-submit hook for ordinary ChatGPT website conversations. Our conclusion is
that mandatory lookup needs a host hook, our own controlled model loop, or an
explicit browser preparation flow. [OpenAI MCP guide](https://developers.openai.com/api/docs/guides/tools-connectors-mcp).

Codex hook output enters developer context. A future adapter must keep trusted
wrapper instructions separate from retrieved source text, label that text as
untrusted evidence, bound its size and test malicious stored instructions.
Labeling alone does not eliminate prompt injection.

## What this repository already provides

The current Windows launcher starts a Python service bound to `127.0.0.1` with
SQLite storage and a browser dashboard. It is not yet a standalone desktop
installer. REST, the Python client and the stdio MCP bridge already call the
same scoped memory service. No replacement database is needed for this work.

The [custom agent example](../examples/agent_tool_loop.py) calls `recall` before
its first `next_turn` model callback. This is the existing foundation for
guaranteed ordering in a loop we control. It retrieves handles; it does not yet
implement the proposed consumer preview, complete context budget or automatic
conversation capture. The [integration guide](integrations.md) configures tools,
not automatic hooks.

Reuse these existing operations in the adapters:

| Need | Existing operation | Remaining work |
|---|---|---|
| Current brief and question search | `MemoryClient.context()` and `recall()` | Select and serialize the final brief/evidence within one overall budget. |
| Exact evidence | `expand(id, version)` | Carry receipts into the preview and prevent stale insertion. |
| Capture a source message | `message(...)` | Explicit capture controls and stable conversation/message IDs. |
| Propose a durable fact | `propose(...)` | Opt-in extraction and review; no blanket acceptance of model responses. |
| Revisions and connection status | `changes(...)` and `connect(...)` | Show lookup, insertion and capture status separately from a heartbeat. |

The API currently rejects cross-origin browser calls. Do not weaken that
boundary to make a content script work. A registered native host can call the
existing loopback API as a local client, with its own narrowly provisioned
credential. The native host still needs sender validation and operation limits.

## Browser and Anthropic capability table

| Integration | Official capability verified | Proposed Q-MDM approach | Limit |
|---|---|---|---|
| Claude Code | `UserPromptSubmit` runs before prompt processing and can return `additionalContext`. It adds context alongside the prompt; it cannot replace that prompt. | A local hook retrieves memory and emits a short context block. Package configuration in a Claude Code plugin once tested. | Only the configured host invokes the hook. This is not a universal web-chat hook. [Hooks reference](https://code.claude.com/docs/en/hooks). |
| Claude Desktop | Desktop extensions package local MCP servers as `.mcpb` files. Custom installation is available in Settings, Extensions. | Package the existing memory tool bridge as a local desktop extension. | Exposing tools does not establish that the model will call memory on every turn. [Local MCP setup](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop). |
| Claude web | Remote connectors are available across Claude products. Local desktop extensions are not available on web or mobile. A plugin referencing local MCP has a different availability matrix from a Desktop extension. | Offer a remote connector only as an optional hosted route. Use the browser/native-host route for the local-first web experience. | A cloud connector cannot be assumed to access a user's private localhost service. [Connector availability](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors). |
| Chromium browser extension | Content scripts can read and change the page DOM and exchange messages with the extension. | Add a visible "Use Q-MDM memory" composer control, then preview and insert the retrieved context. | This requires a site adapter. Editor changes can break it; there is no verified universal composer interface. [Content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts). |
| Browser-to-desktop bridge | Chrome native messaging communicates with a registered local process through standard input/output. The host allowlists exact extension origins. | Extension service worker calls a narrowly scoped native host, which retrieves from the local memory service. | The user must install/register the host separately. Content scripts cannot call native messaging directly. [Native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging). |
| Browser network modification | Declarative Net Request supports blocking, redirecting, upgrading URLs, allowing, and changing headers. Its action schema has no request-body replacement action. | Use visible composer augmentation rather than claim transparent POST-body rewriting. | Most MV3 extensions cannot use `webRequestBlocking`. Observing a request body is not an API for replacing it. [DNR actions](https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest#type-RuleActionType), [webRequest](https://developer.chrome.com/docs/extensions/reference/api/webRequest). |

## Proposed native messaging boundary

```text
Supported website composer
    -> Q-MDM content script
    -> extension service worker
    -> registered native messaging host
    -> local Q-MDM retrieval
    -> extension preview
    -> user-approved context inserted into composer
    -> website sends its normal prompt
```

Chrome requires `nativeMessaging` in the extension manifest. Its host configuration uses `allowed_origins` without wildcards. The service worker must validate the sender origin or URL and sanitize the payload before forwarding messages, because the content script shares a renderer with an untrusted page. These are documented boundaries. [Native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging).

The following are proposed Q-MDM controls, not shipped features:

- Request access only to supported chat sites. Use optional site permissions where practical, with per-site enable/disable controls. Chrome documents runtime optional host permissions. [Declare permissions](https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions).
- Limit native-host operations to typed retrieval and explicitly approved capture. Do not expose arbitrary shell execution, arbitrary file paths, arbitrary URLs, or unrestricted SQL.
- Keep the workspace credential in the native application. Do not put it in the site's DOM or page JavaScript. The content script receives only the selected context and receipt.
- Scope retrieval to the selected personal workspace and conversation/project. Enforce item and token limits in the local service rather than trusting values supplied by the page.
- Require a visible preview before first insertion. Show which memory leaves the computer and where it will be sent. An optional automatic mode must be a separate, per-site choice.
- Store captured messages as source events. Treat model responses as derived content, and proposed facts as candidates. Never make every generated sentence verified memory.

The extension can keep a native messaging connection or reconnect when needed. Its service worker is not the permanent database process. The desktop service owns durable data and recovery.

## Why a universal request interceptor is the wrong promise

Chrome's `webRequest` can expose body data when requested, but its documented `BlockingResponse` does not provide a replacement request-body field. Normal MV3 store extensions also lack the blocking permission available to policy-installed extensions. DNR's supported actions similarly do not include arbitrary JSON-body rewriting. These findings rule out describing those APIs as a general "insert memory into every request" facility. [webRequest reference](https://developer.chrome.com/docs/extensions/reference/api/webRequest), [DNR reference](https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest).

Modifying a site's JavaScript or private network protocol would be a separate, brittle integration. This research has not tested it or established provider approval. Composer insertion gives the user an inspectable result and avoids dependence on private API payloads. It still needs real account testing for keyboard submit, attachments, regenerated responses, streaming, and editor updates.

## Automatic use and native memory

A Claude Code hook can perform local retrieval on each submitted prompt. Keep its output below the documented 10,000-character per-string limit and configure a short deadline. The current documentation says prompt processing waits for the hook. A slow or stuck memory lookup can therefore delay the agent. The proposed behavior is to show an unavailable status and let the original prompt continue after a bounded failure. [Hook timing and output](https://code.claude.com/docs/en/hooks#userpromptsubmit).

An MCP server provides tools; it is not itself an every-prompt interceptor. A `.mcpb` package makes installation easier, but does not change that distinction. Claude Desktop supports sensitive extension configuration fields and stores them using operating-system secure storage. [Desktop extension setup and configuration](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop).

Do not invent a precedence rule where Q-MDM always overrides native memory. Preserve timestamps and sources, label outdated or conflicting memory, and present it as external evidence. Offer guidance for provider-native memory controls separately, based on that provider's documented settings.

## Publication and verification limits

A browser extension handling conversations needs a clear privacy policy even when processing and storage stay local. Chrome's policy explicitly includes local-only handling and website content. The policy should explain capture, insertion into a cloud prompt, retention, deletion, and optional remote connections. [Chrome user data FAQ](https://developer.chrome.com/docs/webstore/program-policies/user-data-faq).

## Recommended build sequence

These are proposed milestones, not delivered features or release dates.

1. **Package the local service.** Ship a Windows desktop launcher/installer that
   includes its runtime, starts the existing service, opens the dashboard and
   reports storage location and service status. Keep hosting and startup-on-login
   optional. Add backup/restore checks, private credential storage and an
   uninstall choice that preserves user data. The development checkout's
   plaintext `.local/keys.json` is not the intended consumer secret store.
2. **Add automatic hooks for supported agents.** Build separate Codex and Claude
   Code packages around the same retrieval code. On each submitted user prompt,
   perform scoped retrieval before the initial model call. Restore appropriate
   context after session compaction through the host's supported lifecycle.
   A healthy heartbeat alone must not mean the hook ran. Default to a short
   deadline and a visible failure; an explicit require-memory mode must block
   continuation when the host supports blocking. Never silently claim memory
   was applied after a failed lookup.
3. **Ship a Chromium browser pilot.** Install the native messaging host with the
   desktop app. Start with one ChatGPT composer adapter and a visible
   **Prepare with memory** action, then add Claude behind the same contract.
   Show workspace, destination, selected evidence and the exact text to insert.
   Let the user send through the site's normal controls. Add opt-in automatic
   augmentation only after each site's submit paths pass testing. Ordinary
   website submission remains possible; do not advertise guaranteed interception
   of all Enter keys, voice input, retries, mobile apps or other browsers.
4. **Add controlled capture and optional connectors.** Capture only messages the
   user agreed to retain, with role and source metadata. Exclude Q-MDM-inserted
   context from recapture so it does not become self-reinforcing evidence.
   Offer eligible native desktop MCP packages and cloud/tunnel connectors as
   separate choices. Disable browser augmentation for a conversation using
   another Q-MDM route unless the user deliberately chooses both.

### Proposed browser state and failure contract

```text
Off -> Ready -> Retrieving -> Preview -> Inserted
                    |             |
                    +-> Error     +-> Draft changed: retrieve again
```

Bind every result to the tab, conversation, workspace and original draft digest.
Discard it when the user edits the draft, switches workspace, navigates, or a
newer request replaces it. Make insertion idempotent and keep the original draft
recoverable. Handle keyboard input methods, existing attachments and a rerendered
editor without deleting user text. If the site adapter is unsupported, show a
copyable context block and an honest unsupported status.

Do not report **used by model** after insertion. The adapter can establish that
context was prepared or inserted, and may observe a submitted visible message;
it cannot observe the provider's internal reasoning. Capture remains a separate
setting, disabled by default. Provide pause, per-site disable and an exclusion
for conversations the user marks private. Do not infer a provider's private-chat
state unless that site's adapter reliably exposes it.

### Release checks and investor demonstration

Use synthetic data and visibly distinguish planned features from running ones.
The proposed demonstration saves a sourced preference locally, retrieves it in
one supported agent, then prepares a relevant prompt on another supported host.
Next update that preference and show the new source/version replacing the old
one. The local activity view should show what left the computer and why.

Before calling a milestone complete, prove:

- Lookup occurs before the model callback in a controlled agent loop; configured
  hooks run on real submitted prompts and handle unavailable memory visibly.
- Browser preparation, insertion, draft edits, navigation, two tabs, duplicate
  clicks and an offline native host preserve user text and prevent stale context.
- Private workspaces cannot retrieve one another's sources. A page cannot obtain
  credentials, choose an arbitrary local URL, execute commands or auto-promote
  malicious source text through the native host.
- Irrelevant questions receive no unnecessary personal memory, corrected facts
  replace outdated ones, and generated text remains source-labeled candidates.
- A fresh install works without a developer Python setup; restart retains data;
  backup/restore preserves revisions and uninstall respects the user's choice.

Record actual lookup/preparation latency, context size, stale/irrelevant insertion
rates and supported-submit coverage on a fixed test set. Compare no memory,
manual context, and Q-MDM using the same model and questions. Do not infer answer
quality, token savings or a quantum advantage from a graph animation. End-to-end
answer quality and native-memory interactions need real host evaluations.

This research opened the official pages cited here. It did not test a browser extension against authenticated ChatGPT or Claude accounts, install native hosts, change user settings, package a desktop application, or obtain extension-store approval. The browser extension and automated hook remain proposed until implementation and end-to-end checks establish otherwise.
