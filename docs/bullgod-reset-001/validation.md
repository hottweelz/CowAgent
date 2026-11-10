# Validation and preservation

## Source and local regression — PASS

Base master is `f659349785acf98905901a5cc53921436a109dbc`. The candidate was
tested before commit; [local-validation.json](local-validation.json) binds all
nine changed application/launcher/test files by SHA-256 before and after the run.
All pre/post hashes match. Final staging exposed one extra blank line at the end
of the new foundation test file. It was removed after the run; the Python AST is
identical. The receipt retains both the tested and published hashes. No behavior
changed, and the suite was not repeated for that whitespace-only correction.

One full guarded directory-mode run on macOS / Python 3.13.1 completed in
208.65 seconds: **5,999 passed, 36 skipped, 93 subtests passed, zero failures or
errors**. JUnit contains 6,128 records including subtests. The receipt lists all
36 skipped IDs and the log/JUnit hashes. There were 35 warnings. Skipped Windows,
native-browser and platform-specific behavior is not claimed as tested.

Reproduce with an existing dependency-complete CowAgent virtual environment and
prepared public tokenizer cache:

```sh
TIKTOKEN_CACHE_DIR=/absolute/path/to/tokenizer-cache \
  /absolute/path/to/venv/bin/python scripts/ci_test.py tests/ -q \
  --junitxml=/absolute/path/to/private-output/full.xml
```

The existing wrapper supplies isolated test HOME/data and guards Python network
connections. Its documented limits, including native/subprocess networking,
remain unchanged. No test guard, skip policy, CI workflow or dependency manifest
was weakened. Private raw evidence is retained at
`/private/tmp/cow-bullgod-reset-001-ogT6Xa` (directory 0700; log/XML 0600).

Focused checks before the full run passed: 143 foundation/audio/operator/
dispatch/discovery cases; 64 foundation/dispatch/operator cases after the
read-only lock fix; and six developer-launcher cases. These selections overlap
and must not be summed into a unique test count. Final full-suite evidence covers
the final code, including the new lock regression. Changed-file Ruff F checks,
launcher compilation, receipt JSON and diff checks passed.

## Independent engineering review — PASS

One Sol 6.1/high reviewer examined extracted authority/ownership controls,
read-only journal methods, provider precedence, the fixture correction, launcher,
tests and retained development receipts. Stronger reasoning was selected for
the security boundary across SQLite, process ownership and the OS sandbox.
No open findings remain.

The review found that a read-only journal inherited an execution-lock method.
The fix rejects before file creation or `flock`; the new regression checks both
operations and unchanged directory membership. The launcher now uses a
default-deny sandbox and prints only the credential file path. Review did not
repeat accepted service interactions or inspect live private data.

## Isolated runtime — scoped PASS

[development-validation.json](development-validation.json) records actual
CowAgent startup, console/authentication, profile, workspace and session checks.
Separate instances had separate stores, and a synthetic ConversationStore
message survived restart. The final default-deny revision passed fresh service,
login, workspace and store-read checks, plus denied outside-root file/network
canaries. The receipt distinguishes earlier persistence observations from final
sandbox observations; it does not imply a complete replay on every revision.

All owned instances are stopped. This is actual application/store integration,
not a model conversation acceptance. No real-model quality, every possible IPC
operation, Windows launcher, production drain or live deployment is certified.
The future PERSONAL-001 scenario remains a separate product acceptance.

## Hosted CI and production — not claimed

No new hosted run was manually requested, and no Actions setting was changed.
Hosted availability is not a product defect or a prerequisite for developing
PERSONAL-001. Existing workflow gates remain intact; prior branch results are
not relabeled as passing results for this candidate. Fresh hosted compatibility
results remain an integration requirement if the maintainer's merge policy
requires them. No Linux or Windows execution is claimed for this candidate.

The [preservation receipt](preservation.json) records the original PID 28093,
healthy `127.0.0.1:9899`, unchanged primary checkout, seven original untracked
files, five recovery artifacts, recovery refs and all four PR heads. No live
memory/data was read or changed for these checks. No service signal, ownership
change, credential refresh or production activation occurred. PRs #4–7 and
their histories/reports remain preserved and unchanged.

## Publication scope

The proposed consolidation is [draft PR #8](https://github.com/hottweelz/CowAgent/pull/8),
implementation commit `4595d81a9efac649034f1d7f4b35d92376442e83`, targeting master
on `codex/bullgod-reset-001`. Push/fetch confirmed upstream counts `0 0`. It does
not merge, close, rebase, force-push or delete any existing branch or PR. The
original untracked workspace `AGENTS.md` remains outside the commit. The draft
PR is for review of this independent baseline; integration is a separate decision.
