# Live accounting gate and Phase 2 description compression

The live Phase 1 gate passed before tool-description edits began. Phase 2 is
complete on `audit/efficiency-001-context-cache`; no merge or deployment is part
of this work. [Numeric verification](phase2-verification.json) contains counts,
hashes and provider usage, with no prompt bodies or credentials.

Subsequent work: [Phase 3 prefix stability](phase3.md) is complete. The results
below describe Phase 2 at its original implementation boundary.

## Live Phase 1 gate

The web server was initially stopped. Verification used the current source and
a private copy of TestPilot's existing workspace, with SQLite read-only backups.
The normal web chat/Agent pipeline called Nemotron and persisted the test run in
that copy. Global credential-file bootstrap was skipped; configured credentials
were used in memory. Production memory, history, configuration and instruction
files were preserved. This proves the live pipeline on a copy, not a production
restart or deployment.

Both requests sent all **16 tools**. The original indexed-memory lookup called
`memory_search`; FTS5 returned one row and no LIKE fallback ran. Raw provider
usage matched the per-request records, latest request and persisted run sum.

| Scope | Input | Output | Cache reads |
|---|---:|---:|---:|
| First provider request | 9,994 | 83 | 0 |
| Latest provider request | 10,271 | 73 | 0 |
| Cumulative run, 2 calls | 20,265 | 156 | 0 |

The live context chart showed **9,561 estimated** tokens: system 4,496, injected
tools 4,695 and updated history 370. The appended answer makes current context
different from the latest sent request; its estimate must not be compared with
the cumulative run as though they were the same quantity.

The live check found a display gap: the API exposed latest-request usage, but
the card did not render it. Web and desktop cards now show separate exact input
and output counts under **Latest request (actual usage)**. Missing or unreported
counters show unknown; reported zero remains zero and partial coverage is labeled.
The reply tooltip explicitly says **Run total**. Browser assertions and a visual
check confirmed the tools slice, latest 10,271/73, run 20,265/156, two calls and
provider-reported zero cache. No new provider call was needed to verify these
display-only changes.

## Phase 2 change and measured saving

Only description prose changed in `scheduler`, `browser`, `search_files` and
`bash`, including Bash's desktop wording variant. Names, complete parameter
schemas (including their descriptions), types, required fields, enums, defaults
and tool execution logic are unchanged. The full 16-tool inventory remains.

The descriptions retain scheduling/time and trusted-recipient guidance, browser
snapshot/ref and login handoff guidance, content-versus-name search behavior,
and shell platform, output, environment and destructive-operation rules.

Matched public NVIDIA template estimates use identical messages, cwd and the
desktop description variant used by the live server:

| Tool block | Before | After | Reduction |
|---|---:|---:|---:|
| scheduler | 1,037 | 942 | 95 |
| browser | 739 | 687 | 52 |
| search_files | 571 | 542 | 29 |
| bash | 474 | 451 | 23 |
| Four targeted blocks | 2,821 | 2,622 | **199 (7.1%)** |
| All tool blocks | 5,473 | 5,274 | **199** |
| Full request | 9,977 | 9,778 | **199 (2.0%)** |

The earlier standard, non-desktop replay showed 185 tokens saved. Its Bash
wording differs from the live verification process. These are local template
estimates; the provider's exact tokenizer/template deployment remains unverified.

The actual first request fell from **9,994 to 9,795 input tokens**, also **199
(2.0%)**. The adapter-boundary message hashes are identical before and after;
all 16 argument schemas are equal. This is a direct comparison of the first
requests. Continuations contain generated tool calls and answers, so their total
change is not attributed entirely to description compression.

The post-change memory run again returned one indexed FTS result with no LIKE
fallback. Its second request used 10,094 input / 42 output tokens and reported
**8,672 cached input tokens**. CowAgent retained exactly that value, with reporting
coverage for both calls. The full run used 19,889 input / 147 output tokens. This
cache hit is an observation, not a promise of future cache reuse or cost savings.

The measured reduction is below the proposed 20–35% target for the four blocks.
Parameter descriptions remain untouched and safety guidance remains explicit.
No tool was removed or deferred to increase the apparent saving.

## Checks and limits

- Schema regression hashes freeze all four argument contracts from `0469a4f3`.
  An additional before/after comparison confirms all 16 argument schemas are
  identical. AST comparison confirms executable code is unchanged after excluding
  only the top-level description and Bash's two desktop prose literals.
- Focused Python groups passed: 85 scheduler/browser/schema cases; 68 Bash/schema
  cases; 130 search/Windows-guidance cases with six optional skips. These are
  per-run counts, with four schema cases repeated between the first two groups.
  Seven native Chrome ref-action cases passed using private browser profiles.
- Eight Node tests passed for web/desktop actual, unknown, zero, partial and cache
  labels. Web JavaScript syntax, Python F-class lint, compilation, diff checks and
  the desktop production build passed. The prior desktop renderer typecheck
  limitation remains as documented in [Phase 1](phase1.md#limits); no full suite
  or native Windows shell run was claimed.
- Four bounded live auto-selection requests offered all 16 tools to Nemotron,
  without forced tool choice. Each selected the expected tool with valid argument
  types, enums and required fields. Actual isolated execution succeeded: a
  reminder record with no scheduler service delivering it, a local HTML page in
  Chrome, a file-content match, and a fixed `printf` command.
- The prior run's context/usage restored after the private server restarted.
  Source file hashes stayed unchanged. One bounded independent engineering
  review found no must-fix issue. No model, identity, instruction, capability,
  cache-routing or title-budget change was made.

One memory case and four selection cases are useful regression evidence, not an
exhaustive task-quality benchmark. Desktop UI was built and its display functions
tested; the actual visual interaction was with the web UI. Provider cache behavior
can vary by route and request. At this stage, Phases 3–5 remained proposals.

Reproduce the schema/display checks with a private data directory:

```sh
COW_DATA_DIR=/private/tmp/cowagent-phase2-check .venv/bin/python -m pytest -q \
  tests/test_tool_description_contract.py
node --test tests/test_usage_display.mjs
cd desktop
npm run build
```

For a new live verification, first make a consistent private workspace copy.
Route the normal web channel to that copy, retain the configured Nemotron model
and all tools, and repeat the stored lookup in a new session. Compare numeric
provider chunks with `context_usage.last_request.usage` and the persisted reply's
run usage; retain no message or credential bodies. Do not point an implementation
test at production databases. The task's private scripts and receipts are named
in the handoff ledger; they are not required runtime dependencies.
