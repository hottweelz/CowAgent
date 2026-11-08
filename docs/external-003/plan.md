# EXTERNAL-003 local operator decisions

Branch: `feat/external-003-operator-controls`, starting at `fcfd0377`.
The owner selected enrollment and approvals before uncertainty resolution.
No master merge, live dispatch, external-service action or production data access.

## Contract

Use a local OS-account operator contract. Derive the actor from real/effective
UID and require a private, canonical, owner-controlled state directory and regular
private journal files. Never accept `approved_by` from request data. This proves
the local account, not human presence; trusted same-account code is in the trust
boundary. No login service, listener, native credentials or model selection.

Keep a dedicated operator journal at an explicitly supplied state directory.
Reuse TaskStore's WAL/FULL connection behavior. Persist revisioned enrollment and
task decisions plus append-only successful-decision audit rows in one SQLite
transaction. Bind requests to immutable review/task hashes, exact supervisor and
caller/runtime scope, enrollment revision and expiry. Exact duplicate requests
return historical receipts plus current state; conflicting IDs and stale
revisions fail. Revocation/re-enrollment invalidates older task approvals.

All responses retain execution and external actions disabled. This is an
operator decision workflow, not a dispatch gate. Existing supervisor, adapter,
transport, runtime configuration and production journals remain unchanged.
Connecting these decisions to dispatch needs a separately tested atomic boundary.

## Work and acceptance

1. Lead implements `agent/external/operator_control.py`: private local ownership,
   transaction/CAS decisions, replay-safe audit, current status and expiry.
2. Luna implements the bounded `operator_cli.py` wrapper and CLI tests. State
   path is required; init is explicit. No arbitrary command execution or service.
3. Lead and a bounded test worker verify enrollment/task approval, scope/hash
   mismatch, expiry, revocation, duplicate/conflicting requests, restart and
   competing decisions. Use disposable directories and fictional records only.
4. One Sol 6.1 review examines OS identity, private-state checks, revision races
   and replay. Luna is insufficient for this cross-component security review.
5. Run focused Python tests, applicable external/recovery regressions, Ruff F and
   compilation. Retain unchanged UI/native evidence; no unnecessary real calls.
6. Publish source-bound receipts and limits, update README/MEMORY/handoff, commit,
   push the current branch and require fetch plus upstream 0/0.

Previous lesson becomes a check: malformed requests are rejected; valid but
expired/revoked decisions remain inspectable and explicitly ineffective.
