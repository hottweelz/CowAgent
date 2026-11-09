# FIRST-BOOTSTRAP-001 qualification plan

Authorized scope: read-only live metadata, source review, disposable transition and
recovery, independent review, and draft publication. Live execution is excluded.

1. Reconcile PR #4/#5/master, source manifests, prior tests and recovery artifacts
   (Luna baseline worker). Retain valid full matrix evidence when executable files
   are identical; qualify new bootstrap artifacts separately.
2. Inventory actual configured producers, available controls, observation limits,
   and candidate startup/shutdown effects (Luna inventory worker). Configuration
   presence must not be reported as active execution or complete quiescence.
3. Verify PID/start/invocation/listener and pCloud exclusion with allowlisted
   metadata only (lead). Verify 9899 only as the live health endpoint.
4. Qualify SQLite/file preservation and an actual legacy-to-candidate-to-fallback
   process sequence on fictional data and separate port 19886 (Terra 6.1 worker).
   Include WAL transactions, interrupted initialization, migration and recovery
   history. No model calls, live data copies, live signals, or external dispatch.
5. Write candidate-specific proposed commands, residual bounds and recovery
   requirements (lead). Commands must fail closed on missing authorization,
   current identity drift, missing backup, occupied port or expired request.
6. Review once independently at high reasoning after all concrete evidence and
   procedure exist. Fix demonstrated findings and rerun affected checks only.
7. Publish docs/first-bootstrap-001/README.md, receipts and handoff on
   codex/first-bootstrap-001, draft PR targeting codex/bullgod-service-drain.
   Verify sync and preserved recovery artifacts; no merges.

Acceptance: cover all ten requested phases and twelve final questions, choose
one A/B/C legacy class and one GO/CONDITIONAL GO/NO-GO maintenance decision.
Successful fixtures never certify live quiescence. A justified NO-GO is a complete
qualification deliverable when the remaining material risk and shortest remedy
are concrete. Preserve source and avoid adding infrastructure beyond this packet.

Checks from prior lessons: keep live and rehearsal ports explicit; use actual
venv invocation; require full directory-mode integration evidence; authenticate
again immediately before a proposed signal; retain no-replay and closed admission
semantics; sample drain probes only after work settles; preserve all unknowns.
