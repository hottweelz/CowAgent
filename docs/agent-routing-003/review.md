# Independent review

This is the original milestone review. The [integrated merge review](merge-review.md)
records later source changes and their separate validation.

One bounded Sol 6.1/high engineering review covered authentication, native
identity, private-memory ownership, concurrency and the acceptance client.
Stronger reasoning was selected for the cross-target authority and data-integrity
boundaries. The reviewer was read-only and did not launch models, rerun tests,
read private runtime state or modify files. The parent retained lifecycle and Git.

**Final verdict: no remaining actionable finding.**

Two findings were resolved before live execution:

1. P1: resolving the expected memory DB before comparison could accept a symlink
   to the other target's DB. Preflight now checks containment and distinct
   device/inode pairs before Bridge/get_agent initialization. Three disposable
   fixtures cover directory symlinks, file symlinks and hard links.
2. P2: the acceptance flag could be set before preservation checks. It now
   requires matching pre/post snapshots, owned-process exit and zero caller
   guarded-private-open attempts. Failure retains a receipt and returns failure.

The reviewer independently checked the sanitized live evidence:

- A: paid 19,800, refunds −2,400, net 17,400 cents; three accepted, two exceptions.
- B: paid 21,450, refunds −1,450, net 20,000 cents; three accepted, two exceptions.
- Dataset hashes and canonical artifact hashes match each report and fixture.
- Target/model/provider/profile bindings match enrollment and discovery. Both
  targets use the same configured model; profile, memory scope, session, run and
  process IDs are distinct. Actual checked memory-scope hashes match inspection.
- Native windows overlap by 13.912434816360474 seconds.
- Each task has one submit, native and publication intent. Signed target/spec
  overrides were rejected; wrong credentials received no authenticated response.
  Duplicate submissions retained their completed native sessions.
- Both statuses are verified, pre/post snapshots match, caller guard count is
  zero and owned processes exited. The parent separately confirmed webserver
  PID 28093 was preserved.
- Current executable-source fingerprint equals the live receipt:
  `fbd5b6a0ecbdcb7dc4aeb6bbb66313c97e7346dc379689ab158a1b681ef09a96`.
- `git diff --check` passes. Parent/worker focused-test results were accepted
  as supplied; the review did not repeat valid test runs.

The verdict covers the bounded experiment and inspected implementation. Local
runtime metadata is not remote provider attestation or OS confinement. File
metadata does not prove complete private-file content equality. Filesystem
mutation by another trusted same-account process after preflight remains outside
the guarantee. No live crash, revocation or cancellation campaign was repeated;
focused tests preserve those contracts.
