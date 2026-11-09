# BullGod service admission, drain and transition preparation

Scope: implement and validate process-owned lifecycle control in an isolated
checkout, then publish a draft PR based on PR #4. Preserve live PID 28093 on
127.0.0.1:9899, APFS ownership, current approvals and PR #4 merge state. The
maintainer's accepted diagnostic finding is closed and is not a gate.

## Design

A small process-wide coordinator closes root admission atomically, counts work
from acceptance through completion/publication, and permits descendants only
through a still-active admitted lease. A child is reserved before thread/pool
submission. Generator scopes cannot leak authority into their caller between
yields. Close is monotonic; timeout does not cancel work or reopen admission.
The coordinator exposes an internal Python API, not an HTTP/chat action. Positive
receipts require a normally initialized runtime owner and complete supported
coverage. Missing participants, untracked external activity or failed state probes
block a drain result. Receipts contain counts and public categories, not payloads.

Cover all registered agent identities in the supported runtime: web request/
response lifetime, chat queue and send completion, direct agent execution,
scheduler/manual callbacks, recovery execution/verification, evolution, memory
and migration background writes. Instrument narrow existing boundaries. Keep
ordinary startup behavior when no close is requested. Non-web transport ingress,
unbounded plugin/cloud/MCP work or other unverified sources must explicitly block
positive drain rather than being inferred idle.

The old live process cannot acquire these hooks through a source edit. This task
qualifies the new control and future transition mechanics in disposable services;
it does not certify old-process quiescence or authorize a bootstrap restart.

## Ordered implementation and owners

1. Lead: record maintainer closure and isolate source from the live checkout.
2. Coordinator worker: common/runtime_drain.py and focused concurrency tests.
3. Channel worker: web WSGI/response boundary, chat acceptance/queue/publication,
   and web/guest worker handoffs; focused channel tests.
4. Background worker: scheduler, recovery and evolution admission/completion;
   focused deterministic worker and verification tests.
5. Lead: startup ownership/coverage/effects, direct agent and remaining background
   integrations, disposable transition driver and final documentation.
6. Integrate one bounded independent engineering review, focused compatibility,
   full protected regression/hosted CI for the executable change, and real owned
   process startup/drain/rollback. Reuse valid evidence for unchanged cases.
7. Publish concrete results and transition limitations; keep live execution gated.

## Shared coordinator API contract

- RuntimeDrain(required_components=()): initially open, process/epoch bound.
- install(coordinator), current(): one process-owned coordinator; absent means
  ordinary helpers are no-ops. Installation must precede background producers.
- work(category, agent_id=''): context manager; nested work may inherit only a
  live lease belonging to the same coordinator. New roots reject after close.
- reserve(category, agent_id=''): lease reserved before asynchronous handoff;
  lease.run(callable, *args, **kwargs) activates and releases in finally; explicit
  lease.release() is idempotent. No raw payload is recorded.
- start_thread(category, target, *, args=(), kwargs=None, daemon=True, name=None)
  and submit(executor, category, target, *args, **kwargs): reserve before starting
  and release on failure or cancellation. Helpers retain ordinary return types.
- tracked(category), tracked_generator(category): decorators for synchronous and
  generator boundaries; no authority leakage across generator yields.
- register_component(name, probe=None): owner-side coverage, optional read-only
  probe returns public blocker codes (empty list means settled). Exceptions block.
- mark_unsupported(code): sticky unknown-coverage blocker, never silently cleared.
- bind_owner(owner): bind the genuine initialized AgentBridge/anchor once.
- close_admission(), wait(timeout), snapshot(): monotonic close and bounded wait;
  no wait while holding a participant's lock and no successful self-drain from
  an active lease. A receipt with missing coverage/owner or blockers is not drained.

If source tracing requires a contract adjustment, coordinate it before editing
shared callers. No worker owns another worker's files; parent owns Git and handoff.

## Acceptance

Prove close versus root admission races, delayed child handoff, cancellation and
failure release, nested/direct generator execution, full response/publication,
scheduler manual/due work, recovery verification and terminal-but-still-running
work, evolution/background writes, timeout/no reopen, unknown coverage, and actual
owned process transition. Test fictional data and stub model boundaries only.
Use the existing guarded test runner and installed venv interpreter:

`TIKTOKEN_CACHE_DIR=/private/tmp/cow-infra-tiktoken-cache <primary-checkout>/.venv/bin/python scripts/ci_test.py <focused selection> -q`

Final commands and results will be recorded after implementation. Startup effects
must be listed explicitly with whether they occur before admission; rollback
cannot undo data writes or recreate the old process. No fresh live acceptance,
approval refresh, ownership change, restart or merge is included.
