# VERIFICATION-001: three task outcomes

Baseline: RECOVERY-001 commit 8ed52509. Branch:
`feat/verification-001-task-outcomes`. User selected native file/artifact checks
first; external-service verifiers remain future work. No deployment or merge.

## Contract

- Preserve task `state` as execution lifecycle. `completed` means the worker
  finished and remains non-replayable even if verification fails.
- Freeze a caller-supplied `verification` contract before dispatch, with separate
  `acceptance` and `external_state` lists. Missing/unsupported checks are
  `unverified`, never implicit passes.
- Native checks: `file_exists`, `text_equals`, `json_equals`, and `sha256` for
  bounded UTF-8 text artifacts. Paths stay inside frozen/current read grants.
  Check records use `id`, `type`, `path`, and `expected` where needed.
- A trusted host verifier reads actual files independently of worker prose,
  tool-result claims and file-list events. It uses the restricted file broker,
  records timestamp/content hash/check outcome, and cannot execute tools or code.
  Filesystem confirmation is scoped to that observation, not a remote service.
- Persist append-only verification reports against task ID, attempt ID and
  contract hash. A stale report cannot certify another attempt. Preserve old
  reports and return three outcomes explicitly through tools/cards/operator CLI.
- Failed/denied tool calls block acceptance even if the model says success.
  Missing artifacts fail checks; inaccessible/unsupported checks stay unverified.
- Run checks after execution commits completion. If interrupted there, restart
  performs read-only verification; it never requeues completed execution.
- `python -m agent.recovery verify TASK --owner AGENT` refreshes observations
  without model execution or task retry. Restricted workers cannot self-certify.

## Owners and work

1. Lead: contract validation/checker, runtime hook, tool parameters/output/cards,
   denied-tool receipts, CLI/service integration, integration tests and docs.
2. Terra 6.1: additive verification storage, attempt/contract fencing and
   serialization; independent unit tests. Interacting durable transitions need
   stronger integration work than routine Luna file edits.
3. Luna: read-only result-path map, then bounded regression execution.
4. One independent engineering review after integration, focused on false
   verification, stale evidence, authority preservation and replay prevention.

## Acceptance and validation

- Real native worker writes correct and deliberately wrong artifacts; both
  executions finish, while acceptance and independent confirmation differ.
- Worker prose claiming success/verification cannot promote either outcome.
- Denied write plus a success summary cannot produce verified acceptance.
- Missing criteria, unsupported external checks and unreadable paths cannot pass.
- Current permission revocation, private files and path aliases stay denied.
- Reports survive reopening; explicit verification observes changed files,
  retains old evidence and does not change attempt count or rerun a model.
- Process death after execution commit but before verification recovers only
  verification. Existing uncertain-effect recovery remains unchanged.
- Focused tests: `.venv/bin/python -m pytest -q tests/test_verification_*.py`.
  Final regression extends the private, spawn-safe RECOVERY selection. Retain
  SQLite/EFFICIENCY/ISOLATION and all RECOVERY cases. No live provider required.
- Nine pre-existing ChannelsPage TS2322 errors remain a documented failed
  baseline, not a passing check. No frontend change is planned.
