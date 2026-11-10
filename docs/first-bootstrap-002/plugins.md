# Seven-plugin lifecycle evidence

Scope: source-mode enabled flags read from the primary `plugins/plugins.json` on
2026-11-09: cow_cli, Godcmd, Keyword, Banwords, linkai, Role and Finish enabled;
Dungeon and Hello disabled. Only these flags were read. The primary Python files
match the candidate base for these plugins; the candidate changes cow_cli and
linkai/midjourney. No loaded-source claim is made for the old process.

Columns: startup; independent producer / async / subprocess; local and external
reads/writes; completion / interruption / coverage / quiescence. No plugin
constructor inspected starts a worker. No direct subprocess call appears in the
seven plugin source trees; delegated code can launch subprocesses. A registered
handler is entered under a plugin lease; completion of a synchronous handler is
its local return, not proof of downstream remote completion. The manager marks
unknown source, changed class identity, and unexpected handlers unsupported.
Scan imports disabled packages too: nine reviewed source trees are hash-checked
before import; any unknown tree and every rescan produce a sticky blocker.
The old process is not instrumented.

| Plugin | Startup | Producers and effects | Completion and qualification |
| --- | --- | --- | --- |
| cow_cli | Builds command aliases and handler. | Event commands can read/write configuration, files, skills and memory, call providers, and publish results. Dream and index rebuild each spawn a worker; skill installation uses a timed future and may run subprocesses via delegated code. | Both threads and future retain leases through local completion and notification; CLI dispatch remains sticky unsupported because its extensible delegated commands can create untracked effects. |
| Godcmd | Reads/repairs admin config, may write defaults, initializes admin state and handler. | Event-triggered administration can change config/session/plugin state and invoke install/update code. Authorization checks remain in the handler. | Local callback covered; external plugin management marks unsupported. Reloaded classes require renewed qualification. Durable operations may be interrupted. |
| Keyword | Reads or creates keyword config and registers handler. | Event-triggered match may fetch a remote file and write a temporary file or produce a URL reply. | Handler covers the synchronous fetch and write; the later channel publication is governed by the channel. A partial external/file effect cannot be undone by drain. |
| Banwords | Reads/repairs config and reads optional word list; registers context and optionally reply decorator. | Event-triggered filtering and reply mutation. No direct asynchronous path found. | Both permitted handler shapes are checked and locally covered through return. Config repair is durable. |
| linkai | Reads configuration, creates MJBot and an event loop object; registers handler. | Events can send messages, upload/read/delete a file, make summary/API requests, or start a Midjourney poll thread that publishes results. Remote job can outlive polling. | Poll and both send calls retain child lease until return. Remote generation/operation marks sticky unsupported because the remote task may survive timeout or failure. Summary is local-call bounded, not remote rollback. |
| Role | Reads role JSON and optional extension files, creates handler. | Event-triggered session setup, clearing and prompt changes through the bot. No direct async producer found. | Local callback covered through return; delegated bot/session behavior and later output remain separately governed. |
| Finish | Registers handler. | Event-triggered unknown-command reply mutation; no independent producer or external write found. | Synchronous local callback covered through return. |

Candidate qualification uses exact expected module/class, source hashes, original
constructor path, compiled class-method signatures, handler shapes and class
identity across reactivation. Hashes
are a maintenance contract, not an attestation of the old PID or a sandbox against
same-user code. Startup and event calls are tracked. Direct calls through the
cloud CLI `execute` entry are also tracked. A qualifying idle fixture does not
prove every provider, publication, or delegated operation has completed.
Midjourney's external job and CLI/plugin-management delegation stay denied when
used. Constructor exceptions, unknown plugins and reloaded classes fail closed.
The independent source review cleared the known import/handler qualification
findings. These class checks do not establish the integrity of every imported
helper or every delegated lifetime; unsupported paths retain their blockers.

Tests: `python3 -m pytest tests/test_plugin_lifecycle_bootstrap.py
 tests/test_cow_cli_install_timeout.py tests/test_plugin_activate_no_duplicate_listeners.py -q`
passed 24 including constructor and import failures, missing configured plugins, wrapped-method replacement, unknown disabled import, scan and reload regression. Seven real constructors were instantiated with fictional config and
network-free setup; callback, a held polling stand-in, held install future,
closed admission and unknown-plugin denial were checked. This is not a full
private-server startup, a provider replay, a graceful process shutdown test, or
verification of every publication path. Original PID remains unobserved.

The subsequent [real service receipt](integration.json) starts all seven enabled
plugins with fictional configuration, holds a real Keyword callback through a
network stand-in, runs the shipped operator CLI, then verifies completion,
unsupported-handler denial and graceful process exit. The supplemental
[seven-plugin receipt](plugin-callbacks-integration.json) observes each actual
registered handler under a lease on neutral voice input and rejects all seven
after close. It selects one listener at a time only inside the fixture. Neutral
guard coverage does not exercise every text command or provider operation.

## Source-mode configuration flags

Read 2026-11-09 from the primary source tree, without recording values of
credentials, prompts, URLs, keywords, or word lists. These are file observations,
not an attestation of configuration loaded by the legacy process. The combined
`plugins/config.json` is absent. The primary root `config.json` was absent or
unreadable; effective in-memory and environment configuration was not inspected.

- cow_cli: no local plugin config; command aliases can still come from global
  runtime config. Godcmd: no local plugin config, so candidate startup repairs
  defaults and may write its config file. Finish has no local plugin config.
- Keyword: local config exists, with zero keyword entries and therefore zero
  configured file-download replies in that file. Runtime configuration can change.
- Banwords: local config has an action, `reply_filter` is true, and the optional
  word file is absent. Thus the candidate registers both covered handlers, but
  has no file-supplied banwords at this observation.
- linkai: local config absent; the template exists and candidate fallback forces
  local Midjourney and summary enable flags false. Its template group app map
  is nonempty; that alone does not establish a usable application mapping.
  Remote app settings can enable those branches when an app code is supplied,
  and the plugin can change settings at runtime. Do not infer these effects are
  impossible. Remote image jobs retain the explicit sticky blocker.
- Role: role catalog exists with 40 entries and no extension directory at this
  observation. Local plugin config is absent; the constructor reads the catalog.

If a constructor fails, `plugin_initialization_failed` stays in the coordinator
receipt even when the manager disables the plugin. This prevents a successful
receipt from silently treating a failed seven-plugin startup as qualified.

Import failures and enabled-but-missing registrations also produce sticky
blockers. Method verification compares raw code; the sole accepted decorator is
the expected `cow_cli.execute` drain wrapper with its target and category checked.
