# Integrated merge review

This gate covers AGENT-ROUTING-001 through 003 against master `9cd8c535`.
Draft integration review: [PR #1](https://github.com/hottweelz/CowAgent/pull/1).

The starting feature head was `d696114e`, three commits ahead with no divergence.
The maintainer authorized baseline repairs after the complete regression found
failures. Master must remain unchanged until the gate passes.

## Repairs and compatibility

- The legacy 001 acceptance client now resolves denied roots before comparing
  them with attempted file opens. A disposable audit-hook probe reproduced the
  alias gap and proved the correction without calling a model. See
  [legacy-guard-check.json](legacy-guard-check.json).
- Guest wrappers were not in the exact native tool descriptor table. This
  prevented real guest turns from executing approved tools. The repair accepts
  only supported exact wrapper/native pairs and validates tool names, path keys,
  write mode, exact GuestAgent membership and work-root binding. PathGuard maps
  guest paths before the native gateway. Restricted file operations still use
  FileBroker; restricted privileged calls stay denied.
- Old executor fixtures used `agent=None`, incomplete Agent substitutes or
  unknown toy tools. Repaired fixtures retain the real permission gateway and
  use registered tools with controlled execution bodies. Raw exceptions remain
  sanitized. MCP transport-result tests and authorized executor-result tests
  exercise their separate contracts; MCP execution remains denied by policy.
- Legacy remote invocation tests now assert the existing unsupported-authority
  denial and prove no bridge invocation. Existing local alias tests remain.
- The Bash fixture quotes the Python executable for checkout paths with spaces.
  The image fallback fixture uses a real lightweight Agent for request accounting.

The guest failures reproduced on an archived master checkout. The other repaired
fixture and underlying implementation paths were unchanged from master. These
were baseline failures, not demonstrated defects in named-agent delegation.

Existing Codex enrollment, operator approval, supervisor, transport and generic
delegation contracts remain unchanged. Named enrollment uses exact runtime IDs
`cowagent.testpilot` and `cowagent.testpilot2`. Result metadata is additive under
`cow.cowagent/1`. Memory aliases fail preflight; settled recovery history is
allowed. The legacy inspect/serve defaults still select TestPilot. New source
requires new source-bound enrollment and task approval. No persistent service
activation is part of this merge.

## Review and evidence

The lead performed an integrated self-review. One independent Sol 6.1/high
reviewer inspected authentication, private-memory ownership, recovery,
compatibility and the guest repair. These cross-target authority boundaries
justify stronger reasoning than routine fixture review. The reviewer found the
legacy guard alias issue; the correction was checked. No actionable guest-policy
finding remained. Model selections were requested explicitly; the runtime does
not independently expose effective worker model identity.

Focused guest/isolation checks passed 107 tests. Local fixture checks passed 17;
inbound and local alias checks passed 25. The first four authority-fixture files
plus guard checks passed 31; the remaining five fixture files passed 52. The full regression receipt retains
the original failures and runner errors separately from the final gate:
[full-regression.json](full-regression.json). The first stdin driver was not
spawn-safe on macOS; the corrected file-backed driver uses a main guard and
directory-mode collection. Only two untracked conflict copies are excluded.

The web JavaScript tests passed 39 cases. Strict desktop TypeScript checking and
the desktop build passed. Existing asset, Browserslist and chunk warnings are
recorded in [merge-ui-static.json](merge-ui-static.json). These results remain
valid because subsequent repairs did not change UI source.

The full-suite environment includes the four supported optional document-parser
packages from `requirements-optional.txt`. Environment state is retained in the
temporary runner's requirements manifest; repository requirements are unchanged.
Windows-only tests require a Windows host. Local browser fixtures use separate
temporary profiles and local HTML, without the user's browser profile.

The prior native receipts remain historical evidence for their recorded source.
The guest policy change alters the executable fingerprint, so a fresh paired
acceptance is required before merging. The existing webserver must stay running.

## Full local regression

The final run passed **5,912 tests**, with **24 Windows-only skips** and **93
passing subtests**, in 225.67 seconds (exit 0). All 706 tracked test files were
included. JUnit reconciles 5,936 named cases plus 93 subtests. All 12 opt-in native
browser cases passed; no optional document-parser test was skipped. Source/test
hashes matched before and after the run. The 36 warnings and shutdown logger
output are retained in the receipt; they did not produce a test failure.

The immutable full regression receipt SHA-256 is
`ebe2fedfd589188982853989d0729c45a83b2a81d258542b5fbf76f4b16fa307`.
That receipt precedes the journal-race repair below. Current Ruff F and AST
parsing also passed on all 30 changed Python files; see
[merge-final-static.json](merge-final-static.json).

## Fresh native acceptance

The first fresh pair failed closed. TestPilot returned only an opening brace,
which the fixed output contract rejected. The client stopped on an uncertain
native observation and terminated the paired owned processes. Each task has one
submit intent, one native intent and zero publication intents. Both postflight
snapshots match; caller guarded private opens are zero. The old attempts remain
non-replayable. See [attempt 1](merge-native-attempt-1.json) and the
[diagnosis](merge-native-diagnosis.json).

The maintainer explicitly authorized one new pair with fresh task IDs and
approvals, with unchanged native models and configuration. This second pair also aborted before publication, when the operator journal
privacy guard rejected a file observation. Each task again has one submit/native
intent and zero publication intents; both snapshots match and owned processes
exited. See [attempt 2](merge-native-attempt-2.json) and its
[diagnosis](merge-native-attempt-2-diagnosis.json). No further native pair is
authorized yet, and neither attempt counts as successful live acceptance.

## Journal race repair

A model-free four-process reproduction of real OperatorControl connections
produced 78 guard errors from 78 otherwise-private owner-matching WAL/SHM
observations with link count zero. SQLite can unlink these sidecars while another
connection inspects them. The fix rechecks only this transient sidecar case, at
most four observations. Each extant observation must still pass type, owner and
mode checks. Missing sidecars or valid replacements can proceed; hardlinks,
symlinks, foreign owners, broad modes, persistently zero-link files and a
zero-link primary database remain denied.

The repeat observed 80 zero-link sidecars with no errors. The fixture proves a
real source of the same error; it cannot prove which stat field caused the
earlier live abort. The exact observed mode/link data were not retained by that
live run. Focused operator and approval checks passed 43 cases. The independent
reviewer found no actionable security gap. See
[merge-journal-race-check.json](merge-journal-race-check.json).

The full regression on the repaired executable source passed **5,920 tests**,
with **24 Windows-only skips** and **93 passing subtests** in 224.75 seconds,
exit 0. JUnit reconciles 5,944 named cases plus 93 subtests. All 12 native browser
checks passed; no optional parser cases were skipped. See
[merge-final-regression.json](merge-final-regression.json). The earlier full
receipt remains immutable because it was bound to the two live attempts.

Final source fingerprint:
`c45ddab4aa00d8c57dc6c9b7370739ab6ee1a7e5f8fcd90381a565d49506f2ae`.
## Final native acceptance

The maintainer then explicitly authorized one final fresh pair on the repaired
source. Both targets passed. See [merge-native-receipt.json](merge-native-receipt.json).

| Target | Task | Net cents | Native PID |
| --- | --- | ---: | ---: |
| testpilot | 3eb473eb-440e-44f2-bad7-fdfe7f4ff865 | 17,400 | 44244 |
| testpilot2 | af67b10d-694d-48a0-850d-f872c5625232 | 20,000 | 44248 |

Each target has one submit, native and publication intent. Separate identity,
profile, memory-scope, session, run and process bindings match native inspection.
The native windows overlap by 9.822101116 seconds. Both exact reports and hashes
were independently recomputed. Authentication negatives and duplicate handling
pass. Tool events and caller guarded private opens are zero; native pre/post
snapshots match and owned processes exited. Existing server PID 28093 remains.
Fresh task IDs differ from both aborted pairs; no old task was replayed.

The independent reviewer confirmed the final source/probe/receipt bindings:
source `c45ddab4aa00d8c57dc6c9b7370739ab6ee1a7e5f8fcd90381a565d49506f2ae`,
probe `47d8ac15c5693631776770872f7670abfe9efceab13892f5fbaa03470d1ecc07`,
receipt `8b7c561fb9effc8ca1585ef2f9bb79fcd73d8eaa95d6e132803a9370af02cf55`.
There is no outstanding source or native finding. Prior failed attempts remain
retained and are not counted as successful acceptance.

## Linux compatibility gate

Hosted Actions did not dispatch a run despite enabled permissions, an active
workflow, a same-repository PR and multiple valid trigger opportunities. The
read-only audit could not establish a cause. No hosted CI success is claimed;
[merge-hosted-ci-status.json](merge-hosted-ci-status.json) records the observation.
No branch rules require hosted checks. The maintainer required full regression
and compatibility review, not a particular hosted runner. The lead therefore
selected equivalent disposable local Linux checks for Python 3.11 and 3.13, using
the published source snapshot, while retaining the hosted-CI limitation.

The first Linux diagnostic used a read-only checkout as root, with missing
process utilities and old SQLite 3.40.1. This was not a valid CI environment:
fixtures write within the checkout, permission checks require non-root execution,
and the FTS integrity fixture requires SQLite 3.44+. That run is retained as
setup evidence, not interpreted as a product regression.

Corrected focused Linux checks passed 27 cases, and the FTS case passed on
SQLite 3.46.1. The runner preloads the supported public tokenizer asset during
setup, then disconnects networking for tests. A buffered FIFO fixture also lost
its JSON in 100/100 timing probes; the final unbuffered binary fix retained 100/100
outputs. SQLite fault injection now filters its owned DB to avoid unrelated
background connections. Final host checks on these two files passed 16/16.
These are test-only corrections; executable fingerprint and native acceptance
remain unchanged. See [merge-fixture-followup.json](merge-fixture-followup.json).

Full Linux results remain pending; master is unchanged.
