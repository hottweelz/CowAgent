# DISCOVERY-002S independent review

2026-11-09. **PASS — no actionable source or test findings.**

One Sol 6.1/high reviewer inspected `app.py`, `startup_observer.py`,
`discovery_startup.py` and both new test files. This assignment needs combined
authentication, replay, runtime lifecycle and data-integrity reasoning. Model
selection is recorded; independent effective-model attestation is unavailable.

The review confirmed private canonical request validation, durable exclusive
consumption and path-bound replay rejection, owner validation before private
binding reads, nonzero maintenance failure before channels, and inactive default
behavior. The observer has no HTTP/chat route, adapter contact or dispatch method.
Same-UID/root arbitrary code remains outside this application trust boundary;
the request does not prove human presence or grant task authority.

The independent test owner reported 28 startup tests passed. Tests cover genuine
Bridge/AgentBridge initialization, constructor prohibitions, invalid authentication,
copied/recreated request rejection, launch mismatch, and ordinary source/desktop
startup ordering. The reviewer inspected the final tests and ran only the diff
check; tests were not redundantly rerun for review.

Parent-run real disposable startup/observation/fallback and fresh-process replay
evidence support the bounded process mechanics. They do not certify the old PID's
loaded source, quiescence or data preservation across a live update. Migration and
drain constraints must remain in the maintenance packet. Hosted and integrated
validation are separate gates recorded in their own receipts.

The lead's pre-review corrections ensured nonzero maintenance startup exceptions,
per-request durable claims, canonical request-path binding, and initialized-owner
validation before private reads. No unresolved review finding remains.

## Corrective review after cold-process and hosted evidence

The parent found a cold-import defect after the initial review: an invalid helper
request could create the configured data directory and `run.log` through eager
package imports. The repair makes public exports lazy, extracts the identical
file guard into a pure module and suppresses helper-controlled bytecode writes
until preparation ends. The prior bytecode setting is restored on all exits;
interpreter/site startup itself remains outside helper control.

The reviewer checked the complete corrective delta and public object identities.
The three cold-subprocess tests now use nonexistent isolated data roots for all
cases, closing the initial regression-test gap. Corrective verdict: **PASS**.
The parent integrated selection passes 386 cases. This replaces the original
review's source applicability; hosted and final-fingerprint rehearsal remain
separate gates.

The first hosted run also had three initial-selection denials in existing
runtime-reader tests on Linux 3.13. A deterministic probe demonstrated that the
fixture could yield after socket bind but before listen. The fixture now waits
for the server published after bind/listen and reports sanitized failure codes.
The reviewer confirmed that boundary and unchanged assertions. This fixes the
demonstrated race; it does not prove the cause of the original hosted failures.
