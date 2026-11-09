# DISCOVERY-002S — inactive startup observer

The maintainer authorizes implementation, tests, disposable startup/rollback
rehearsal and a concrete maintenance packet. The existing service PID 28093 must
remain intact. This supersedes the earlier plan-only restriction for source work;
it does not authorize live maintenance, authority refresh or merge.

## Requirements and ownership

| Gate | Required evidence | Owner |
| --- | --- | --- |
| Hook | Launch-only one-shot observer; inactive by default | Sol 6.1/high production worker |
| Authentication | Guarded private request; launch/source/process binding; atomic one-use behavior; no HTTP/chat activation | Production worker plus independent Luna tests |
| Normal startup | Existing source and desktop startup ordering/behavior without maintenance input | Independent Luna tests |
| Disposable rehearsal | Real process launch, initialized observation, health, graceful owned-process exit and fallback launch with fictional state | Lead |
| Migration | Actual schema/marker assessment; disposable compatibility tests; explicit block if live non-destructive behavior is not proved | Luna migration/drain worker |
| Live preservation | PID/start identity remains unchanged; no live task, model, state mutation or restart | Lead plus read-only launch worker |
| Hosted CI | Full required matrix on the final executable fingerprint | Lead and Luna CI worker |
| Review | One independent engineering/security review; concrete findings resolved | Sol 6.1/high reviewer |

The lead owns shared documentation, integration, Git and final handoff. Workers
own disjoint files. Sol is used only for the combined authentication, replay,
startup and data-integrity boundary. No external worker pool is required.

## Ordered work

1. Inspect the current branch, reviewed service plan and latest handoff. Preserve
   all seven original untracked files, recovery refs/artifacts and old receipts.
   Apply the launch-fidelity lesson: a resolved executable is not an invocation.
2. Add the minimal seam in `app.py`, `agent/discovery/startup_observer.py` and
   `scripts/discovery_startup.py`. Validate private launch input before config
   mutations, borrow normal initialization, observe before channels, and fail
   closed with nonzero exit. Keep adapter contact and dispatch unavailable.
3. Add independent negative/default-startup tests in
   `tests/test_discovery_startup_observer.py`. Exercise real private-file guards
   where possible. Test the normal path as well as the opted-in path.
4. Establish interpreter/dependency evidence and all-agent drain requirements.
   Inspect only permitted metadata of live state. Reconcile migration markers
   and add fictional migration/rollback coverage in
   `tests/test_discovery_startup_migration.py` where needed.
5. Run a real disposable startup and fallback rehearsal with isolated HOME/data,
   source artifacts, fictional records and a separate owned listener. Never
   copy live memory or credentials. Record source/interpreter/process bindings,
   observer results, normal startup side effects and rollback limitations.
6. Review the integrated boundary, fix concrete findings, then run focused checks
   through `scripts/ci_test.py`. Publish the executable source and require the
   full existing hosted matrix; do not substitute the prior source's CI.
7. Produce the maintenance packet with actual candidate/fallback commands,
   prerequisites, outage and graceful termination bounds, rollback checks and
   explicit blocked conditions. No live command is executed by this milestone.
8. Audit every gate against receipts, publish concise handoff and verify upstream
   0/0. Keep PR #4 draft and unmerged. Do not claim live readiness from fixtures.

Known constraint at entry: the old process has no trusted drain/inspection hook.
Migration may be explicitly blocked under the acceptance contract. Other missing
requirements remain incomplete until evidence resolves them; do not replace the
requested packet with an open-ended investigation.
