# EXTERNAL-001 design and acceptance plan

Baseline: fork master `e642eec11c4fba1b193d49c7dadb3d02d4667ce0`.
Branch: `feat/external-001-runtime-contract`. No master merge or deployment.

## Selected approach

BullGod is a trusted host supervisor. It does not instantiate an external
runtime as a CowAgent Agent, forward its model configuration, reuse its private
session, or import its credentials/memory/tools. A versioned protocol exposes
discovery, submit, status, cancel and result. Independent verification is a
separate supervisor operation over explicitly enrolled read-only exports.

Options considered: extend legacy PeerTransport.invoke (too little lifecycle
and authority information); embed another harness (violates runtime ownership);
add a separate durable external-runtime protocol (selected). Peer directory
metadata may be reused, but legacy invoke/speak/clear remain denied. No native
restricted tool gains a new capability in this milestone.

The controlled adapter uses a private Unix-domain socket between independent
processes, authenticated request/response envelopes with task identity binding,
and disposable runtime-owned SQLite/artifact storage. It opens no TCP listener.
The wire contract is transport-independent; authenticated cross-host transport
and real agent adapters remain future integration work, not enabled code.

## Frozen interface and owners

- Lead: `agent/external/contract.py`, `transport.py`, `journal.py`,
  `supervisor.py`, independent verifier, integration/process tests, docs and Git.
- Luna/high: read-only existing interface audit.
- Terra 6.1/high: synthetic standalone runtime and its focused tests. Durable
  process ownership, effect boundaries and independent runtime state require
  more than routine Luna implementation.
- One independent Sol 6.1/high security/architecture review. Authenticated
  identity, authority and uncertain effects cross trust boundaries and require
  stronger reasoning than a routine local review.

External records use additive `external_*` tables in the existing TaskStore
database via its WAL/FULL transaction facility. They are separate from native
`recovery_tasks` so the native consumer cannot replay external work. Frozen
task hashes, transport intent, remote identity/session, revisions, cancellation
requests and append-only observations remain durable. No secret is journaled.

## Safety and lifecycle invariants

1. Runtime and supervisor IDs are pinned at enrollment. Messages authenticate
   the protocol version, request ID, target, action, expiry and complete body.
   Credentials expire independently of task grants. Responses bind the request
   ID and cannot regress a task revision or change its identity/session.
2. Supervisor task ID and idempotency key are durable before network I/O.
   Duplicate identical submissions return the same runtime task/session;
   changed input under the same key is rejected. An uncertain send is followed
   by status queries only; no automatic resubmission, even if status is missing.
3. Task authority is a frozen, expiring allowlist of operation and task-owned
   artifact namespace. Runtime policy can only narrow it. No shell, arbitrary
   path, provider selection or private-state operation exists in the fixture.
4. A simulated external mutation requires explicit trusted-host approval bound
   to task hash and expiry. A worker cannot approve itself. Rejected/expired
   grants and approvals cannot produce an effect.
5. Runtime records effect intent before executing and completion after it.
   Restart can continue queued work before an intent; any abandoned mutating
   intent becomes needs_review. No exactly-once external-effect claim is made.
6. Cancellation is a durable request until the runtime reports a terminal
   state and termination_confirmed. A disconnect or timeout is not termination.
7. Transport acknowledgement, runtime execution, acceptance, independent
   artifact checks and independently confirmed external effects are separate.
   A runtime success claim cannot set supervisor verified=true.

## Acceptance evidence

Use fictional tasks, private HOME/data, temporary sockets and fake keys only.
Exercise actual transport and supervisor API with a separate runtime process.
Test discovery, concurrent submissions, duplicate/conflicting keys, host and
runtime restart, lost submit responses, crash after effect before receipt,
cancel request versus termination, expired credentials/grants/approvals, wrong
runtime/task/stale response, artifact mismatch and unsupported verification.
Inspect both journals and actual files/effect rows. Preserve runtime-owned
identity, model, private memory, credentials and session mapping across restart.

Run retained 119-file orchestration regression plus external tests; rerun the
seven opt-in native-browser cases, Node UI checks, strict renderer typecheck,
desktop build and changed Python static checks. Keep platform skips explicit.
Fix concrete independent review findings, publish schemas/receipts/limitations
in README.md, commit/push the branch and verify upstream 0/0.
