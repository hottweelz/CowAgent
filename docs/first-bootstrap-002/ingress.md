# Legacy ingress exclusion assessment

**Result: failed gate; legacy Class C remains.** No supported in-process control
can close all admission in PID 28093. The listener still accepts direct loopback
requests. A gateway can reject its own requests, but the running service remains
reachable around it.

## Observed state

- The service is PID 28093, listening on `127.0.0.1:9899`; the listener was
  confirmed with `lsof` and `netstat`. A read-only `GET /api/health` returned
  HTTP 200 with status `ok`.
- This bind prevents direct connections to the listener through a non-loopback
  interface. It does not prevent another local process from connecting. It also
  does not prove that a tunnel or local forwarder is absent.
- The current channel configuration was previously established as web-only.
  The web route table in `channel/web/web_channel.py` exposes chat (`POST
  /message`), stream (`GET /stream`), poll/cancel, and OpenAI-compatible chat
  (`POST /v1/chat/completions`). Guest message and stream routes are registered
  by `channel/web/api/guest.py`. `/api/scheduler/run` can start a saved task;
  scheduler create/update/toggle routes can affect later work. A complete
  service-level exclusion must cover the whole listener, not only chat paths.
- The web channel starts a scheduler and background threads. Source also has
  plugin-created threads and executors. A network fence cannot settle already
  accepted requests, scheduled callbacks, plugin work, or external effects.
- Read-only process-name inspection found Tailscale and an `ssh` process. The
  Tailscale `serve status` command reported `No serve config`. Process names do
  not establish tunnel destinations; command arguments and private config were
  not dumped. No forwarding to port 9899 was established by this check.
- macOS PF state could not be read: both `pfctl -s info` and `pfctl -s rules`
  returned `Permission denied` for `/dev/pf`. No PF, firewall, route, or network
  configuration was changed. Therefore no OS rule has been shown to block
  loopback access.

## Disposable evidence

`ingress_fixture.py` starts a fake service on `127.0.0.1:19888` and a local
gateway on `127.0.0.1:19889`. It proves that the gateway can reject new chat,
stream, and queued-task requests while still returning health, that a request
accepted before closure completes, and that reopening restores admission. It
also proves direct access to the service on 19888 still succeeds during gateway
exclusion. This is a deliberate bypass demonstration, not a legacy-service
boundary. It used no persistent configuration and did not touch port 9899.

## Shortest concrete remedy

Request approval for one narrowly scoped, temporary host enforcement mechanism
that blocks *all* local TCP ingress to `127.0.0.1:9899` while preserving an
approved observation path. On this host that means a reviewed OS-level rule or
network-extension policy, tested on disposable ports for loopback behavior,
health/observation, held requests, restoration, and unrelated applications
before any rule is installed. The current PF interface is not readable without
additional privilege, and no rule design or installation is authorized here.
If the selected OS mechanism cannot distinguish an observation exception, use
an alternate out-of-band health observer and block the whole service port.
Do not put a gateway in front while direct 9899 remains reachable.

Even a proven network fence would exclude only new external work. It would not
prove the legacy process idle, stop its scheduler, drain accepted work, or
reverse already issued effects. Those remain separately qualified legacy
uncertainties.

## Forwarder evidence limits

A bounded in-memory parser inspected only recognized SSH forwarding flags
(`-L`, `-R`, `-D`, `-W`, `LocalForward`, `RemoteForward`, `DynamicForward`). It
found one explicit forwarding option on the observed SSH process and no
explicit forwarding target containing port 9899. No argument, destination,
environment, or credential value was emitted. This does not rule out forwarding
inherited from SSH config, a wrapper, another unrecognized forwarder, or a
forwarder configured outside process arguments. That uncertainty remains.

The prior fixture stopped both servers in `finally`; subsequent binds to
127.0.0.1 ports 19888 and 19889 succeeded. This confirms the disposable fixture
left no listener on its ports. The fixture is an HTTP transport/gateway test: it
does not run CowAgent route handlers or prove a firewall rule.

## Scoped PF qualification proposal (not applied)

The candidate is a temporary **private PF anchor rule**, attached only through
an already active, approved anchor hook. Do not modify the root ruleset, load
`/etc/pf.conf`, enable PF, or flush global rules or states. A PF anchor that the
root ruleset does not call is inert. The local PF manual warns that `set skip on
lo0` bypasses filtering on loopback; verify the loaded root and anchor rules
first. Local `pfctl` access was denied, so these checks remain unperformed.

Before any live rule, use a separate disposable macOS host/VM and an unused test
port. Construct the test rule with the exact interface and address shape:

```pf
block drop quick on lo0 inet proto tcp from any to 127.0.0.1 port = 19888
```

Parse only the private candidate anchor without loading it:

```sh
pfctl -n -a codex/first-bootstrap-002 -f /path/to/disposable-anchor.conf
```

Then, with separate authorization for the disposable host, load only that
anchor (never the main ruleset), inspect that anchor, and test direct connections
to the test listener. Confirm the test host has an existing active root hook to
that exact anchor and no `set skip on lo0`; otherwise stop. Do not create the
hook by replacing the main ruleset. Test both a new connection and a pre-opened
keep-alive connection. PF state may preserve established flows, so do not claim
that the rule blocks new HTTP requests on an existing connection until tested.
Do not clear global PF states to force a pass. The accepted request may finish;
the test must show whether a pre-existing connection can submit another request
after closure.

If approved on the disposable host, the scoped apply and rollback shape is:

```sh
pfctl -a codex/first-bootstrap-002 -f /path/to/approved-rule.conf
pfctl -a codex/first-bootstrap-002 -sr
pfctl -a codex/first-bootstrap-002 -F rules
```

These commands were **not run**. `-F rules` is scoped to the named anchor. Never
use `pfctl -F all`, `pfctl -F states`, `pfctl -d`, `pfctl -e`, or an unscoped
`pfctl -f` for this operation. Confirm the global rules and state counts remain
unchanged before and after the anchor operation. The rollback is complete only
when the named anchor is empty, the 9899 listener is reachable again, the prior
global ruleset is byte-for-byte or structurally unchanged, and the unrelated
application canary still works.

An attached rule for the final qualification must target the exact live listener
address and port on loopback. PF cannot inspect HTTP paths, so this would block
health too. Use an out-of-band observation path (for example, a bounded local
process/listener check) during exclusion. Do not add a gateway exception: a
gateway that can reach 9899 would itself be blocked by the same rule, and a
gateway exception reintroduces direct-bypass questions. First prove the
disposable rule blocks direct service access from normal local clients and
forwarders, leaves unrelated application traffic intact, and can be removed
without changing persistent config. Only then request separate live-rule
approval.

| Acceptance item | Required PF qualification evidence |
| --- | --- |
| 1. Normal request before exclusion | Chat, stream, queued-task, and health requests reach the disposable listener before rule load. |
| 2. Activate exclusion | The attached private anchor is loaded; exact rule counter increments for the test traffic. |
| 3. Chat/agent rejected | Direct `/message`, OpenAI-compatible chat, guest message, and all other admission paths fail at the TCP boundary. |
| 4. Streaming and queue covered | `/stream`, guest stream, poll/submit, and scheduler run/create trigger paths are excluded. |
| 5. Health observation | The full port block also blocks HTTP health; use an approved out-of-band process/listener observation. |
| 6. In-flight completion | A held request accepted before the rule is allowed to finish; a later request on the same keep-alive connection is separately tested and must be rejected. |
| 7. Alternate-route bypass | Direct 127.0.0.1 access, localhost resolution, supported local tunnel/forwarder and every listener address fail. Any remaining path fails the gate. |
| 8. Restore | Remove only the private anchor rules; new direct requests work again. |
| 9. No persistent configuration changes | No root config edit or startup persistence; global PF rules/state unchanged; named anchor empty after rollback. |
| 10. Unrelated application impact | A preselected unrelated local application canary passes before, during, and after. |

The required direct-bypass result for an enforced boundary is **rejected**. The
HTTP gateway fixture intentionally demonstrated the opposite and therefore
does not satisfy item 7. These PF tests need an authorized disposable host and
are not evidence for this live host. If there is no active root hook or loopback
filtering is skipped, the shortest safe remedy is a separately approved,
process-aware host network extension with a disposable qualification, not a
global PF reload or an untested gateway.

## Ingress route map scope

`channel/web/web_channel.py` is the URL source of truth for the web listener.
Besides chat, stream, OpenAI-compatible chat, guest routes, and scheduler run,
the same listener exposes MCP server test/configuration and OAuth callback,
skill creation/upload, update start, file reveal, voice ASR/TTS, workspace
write, knowledge import/action, and channel configuration routes. Some of these
can start external or durable activity. The disposable fixture covers only the
transport behavior for its named chat/stream/scheduler paths. A port-wide OS
rule is needed because route-level filters would leave alternate routes open.
