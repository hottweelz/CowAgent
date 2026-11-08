# Independent engineering review

Date: 2026-11-07. Delegated reviewer: Sol 6.1/high, read-only.
The assignment required cross-process authority, native ownership and uncertain
effect reasoning beyond routine review. Parent owns lifecycle and Git.

**Result: no remaining blocking finding in the reviewed bounded analysis
implementation.** This supports review of the enrolled operation; it does not
approve unrestricted production orchestration, merge or activation.

## Revised authority assessment

Internal collaboration is not a defect. Public native child activity and fresh
history reads establish native parentage in the observed probes. Actual child
write attempts reached approval, were declined, and left no inside/outside
markers. These results, current profile checks and documented native inheritance
support the bounded analysis contract. Tool names or disabled flags alone would
not establish either an escape or safety.

For the analysis operation, the supervisor-materialized artifact is the only
permitted external effect. Effective native/child controls exclude other effect
channels; a durable publication seal prevents late writes and republishing after
restart. This can satisfy the existing task-effect termination contract while
descendant execution and provider-side cost remain unverified. This reasoning
does not apply to arbitrary-command or external-service adapters.

## Closed findings

| Finding | Correction and regression |
| --- | --- |
| P2: provider digest alone did not bind effective permission scope | Enrollment includes complete config digest; fresh attestation compares the exact effective profile after null/default serialization cleanup. Added-grant and non-provider-drift tests reject the change |
| P2: subsequent explicit cancel was suppressed after a lost interrupt | Persist cancellation intent once; each explicit nonterminal cancel can transmit the bound interrupt again. Status polling never retries. Lost-first/repeated-second regression passes |
| P2: verifier rejected valid long artifact names | Artifact names now use the same identifier rule as the external contract. Valid long-name regression passes |

Independent narrow confirmation passed all four correction tests and diff
checks. During confirmation, the new cancellation test exposed a timing-sensitive
unguarded SQLite read. It now waits through synchronized authenticated status
access; the corrected selection passes. No product result was waived because
of a failing test.

## Scope and limits

Reviewed `codex_adapter.py`, `analysis.py`, `codex_policy.py`, external contract
and synthetic-runtime changes, focused tests, and native authority receipts.
The review covered enrollment, identity, durable dispatch intent, no replay,
publication fencing, cancellation semantics, independent verification and private
IPC reuse. The reviewer made no source edits and ran no real Codex/model tasks;
reproductions and correction checks used disposable fake clients.

No further blocking issue was found in arithmetic/schema verification, explicit
caller-check handling, publication/cancel serialization, monotonic observations
or IPC reuse. Full regression and actual adapter execution were parent-owned
gates and are separately documented in [README.md](README.md).

Uncertain execution remains nonterminal and cannot replay automatically. Native
child exit, hard cost/resource limits, other platforms and broader operations
remain outside the demonstrated guarantee.
