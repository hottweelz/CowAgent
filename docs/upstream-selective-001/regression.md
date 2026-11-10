# Final combined regression run

## Source snapshot

- Worktree: `/Users/jamestylee/.codex/worktrees/upstream-selective-001-desktop/CowAgent`
- Branch: `codex/upstream-selective-001-desktop`
- HEAD: `2ed12245b0549100aa9a5ef858ae512f48eaf7f3`
- Comparison baseline: `74b75f97e933d36e7b1b0a80b8d20afe16cbf8b2`
- Changed source and test paths hashed: 31, including Python backend files and desktop TypeScript/TSX/MJS files.
- SHA-256 manifests: `/private/tmp/cow-upstream-selective-001-final-suite.LmbxD5/source-test-sha256.before` and `source-test-sha256.after`.
- Hash comparison: identical before and after the suite.

## Command

```sh
TIKTOKEN_CACHE_DIR=/private/tmp/cow-infra-tiktoken-cache \
  /Volumes/Predator\ SSD\ GM7\ 1TB/Projects/CowAgent/.venv/bin/python \
  scripts/ci_test.py tests/ -q \
  --junitxml=/private/tmp/cow-upstream-selective-001-final-suite.LmbxD5/full.xml
```

The guarded runner prepares isolated HOME and COW_DATA_DIR values, sets the interpreter directory on PATH, and blocks network connections outside owned loopback fixtures. The required tokenizer cache was reused. No source or test files changed during the run.

## Result

- Exit status: 0
- Passed: 6,360
- Failed: 0
- Errors: 0
- Skipped: 36
- Subtests passed: 93
- Warnings: 36
- Pytest runtime: 220.85 seconds (3:40)
- JUnit testsuite runtime: 220.685 seconds
- JUnit cases: 6,489 (includes the 93 subtests)

The warning summary includes an unraisable WebSocket thread exception (`OSError: [Errno 9] Bad file descriptor`) during `tests/test_youdao_translator.py::TestYoudaoTranslatorInit::test_init_missing_credentials_raises`. Pytest reported it as a warning; the test suite completed with zero failures and errors. Other warning classes include logger deprecations, tar extraction deprecation, and multiprocessing fork warnings.

## Retained output

- Full log: `/private/tmp/cow-upstream-selective-001-final-suite.LmbxD5/full.log`
- JUnit XML: `/private/tmp/cow-upstream-selective-001-final-suite.LmbxD5/full.xml`
- Exit status: `/private/tmp/cow-upstream-selective-001-final-suite.LmbxD5/exit-status.txt`
- Changed source/test path list and SHA-256 manifests: same directory.
