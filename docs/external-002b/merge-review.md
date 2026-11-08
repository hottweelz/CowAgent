# EXTERNAL-002B merge review

Decision: **APPROVED for merge into the fork's master**, 2026-11-07.
The owner explicitly authorized this merge and the start of EXTERNAL-003.
Production activation and broader external actions remain disabled.

Reviewed product commit: `bc88ca4ba91aaff7f7b16a72ab6cf577f303c968`.
Base: `e642eec11c4fba1b193d49c7dadb3d02d4667ce0`.
Ancestry includes EXTERNAL-001 `bfd64e39` and EXTERNAL-002 `26c8e77d`.
Integration uses a fast-forward, retaining the complete evidence and history.
The merge-review documentation does not change the tested product source.

## Gate results

- Independent Luna/high release validation approved the exact product commit.
  It confirmed all 78 static source hashes, all nine native source hashes and
  the verified artifact hash against committed files.
- JUnit contains 1,464 unique IDs: 1,449 passes and 15 skips. The seven exact
  browser reruns give 1,456 unique passes and eight Windows-only skips.
- Accepted Node 39, strict renderer typecheck, desktop build and static evidence
  remain applicable. The initial fixture failure and existing build warnings
  remain documented. No test result was waived.
- The independent [engineering review](review.md) closed its three P2 findings.
  The corresponding drift, explicit-repeat-cancel and artifact-name tests are
  present in the reviewed source.
- No application tool registration, global orchestration startup or production
  runtime configuration is introduced. The native acceptance runner requires
  explicit `--execute`; enrollment remains off by default.
- Legacy credential defaults remain unchanged. The Codex runtime requires
  exactly the bounded analysis grant; broader service effects are unsupported.

The accepted executions were not repeated merely to regenerate evidence.
Source and receipt integrity were revalidated for the merge. No real model call,
production journal mutation or native configuration change was needed.

GitHub reported no commit status or workflow run for the feature commit at the
merge check. This is recorded as absence of remote CI evidence, not a passing
remote check. The local release receipts above establish the reviewed gate.
Docker image-publishing jobs are restricted to `zhayujie/CowAgent`; the fork's
merge cannot satisfy that condition. Release workflows require manual dispatch.

## Retained limits

Approval covers the enrolled macOS/CLI 0.165.0 read-only analysis/artifact
operation. It does not certify all native descendants exiting, hard cost/resource
ceilings, other platforms/configurations or external-service mutations.
The next branch must retain these limits until each new authority and independent
verification contract has its own tests. No live activation follows from merge.
