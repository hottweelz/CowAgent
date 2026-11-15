# customBridge assessment

The owner added `customBridge-main` to the original CowAgent checkout during
this task. It remains an untracked, unchanged package there. This branch does
not vendor, install, register or activate it.

## Answer

It can help **choose** a computer-use route once actual backends are available.
It does not supply the missing Muse/Grok interface or a desktop-control backend.
Use CowAgent's existing browser infrastructure for this POC. Consider customBridge
later as optional route-planning input, subordinate to BullGod's authority and
verification. No new registry or orchestration loop is needed now.

The inspected package is `custombridge` version `0.4.0`, requiring Node >=20.
The 51-file source-manifest digest (sorted path-to-SHA256 map) is
`af7f866a5d847e2d979f34619860ecadde09c2a55487b8390750a2b4142d901b`.
Its README calls it the Aven tester edition; Aven is not required. These are
source snapshot facts, not evidence of a running or configured installation.
Source paths below are relative to the supplied `customBridge-main/` directory.

| Finding | Actual implementation | BullGod implication |
| --- | --- | --- |
| Route selection | `src/planner.mjs:23-72` filters capabilities by requirements and availability, ranks them and returns route status. | Useful planning logic; route selection creates no permission. |
| Computer-use declaration | `src/adapters/runtime-computer-use.mjs:3-32` checks a caller-supplied capability ID. `src/cli.mjs:162-164` reads declared runtime IDs. The adapter does not connect to or test a desktop controller. | `AVAILABLE` is not independent proof that a backend can control the intended app. |
| Browser features | `src/browser-features.mjs:14-67` and `capabilities/browser-features.json:1-20` describe a pinned Chrome DevTools MCP tool catalog and proposed allowlists. | A proposed host configuration is not an installed tool or enforced approval gate. |
| Dedicated Chrome | `src/browser.mjs:67-80`, `src/adapters/chrome-browser.mjs:14-18` launch separate Chrome without a debugging transport. | A browser window is not itself an automation connection. Native CowAgent already supplies Playwright interaction. |
| Receipt logging | `src/receipts.mjs:31-52` validates links to plan receipts. `src/cli.mjs:253-263` accepts a caller-supplied outcome; `src/evidence.mjs:76-117` stores JSONL evidence. | Useful evidence format; not independent result verification or durable remote task reconciliation. |
| Muse/Grok integration | No Muse/Grok adapter or target reference was found in source, target/capability catalogs, docs or README. `capabilities/builtin.json:1-81` lists generic routes. | The precise integration blockers in the two discovery reports remain. |

`SECURITY.md` and the source keep authorization with the caller. This is compatible
with BullGod's ownership model, provided BullGod never treats configuration,
runtime declarations, tool names or caller-reported receipts as authority or
completion proof. Do not import packaged skills into this STE-governed project
as part of this task.

## Checks

A delegated read-only audit inspected source and tests before execution:

- `node --test`: **7 passed**. The tests cover offline catalog/adoption plans.
- `node scripts/check-syntax.mjs`: **passed**.
- No dependency installation, setup, global link, connector call, browser launch,
  skill installation, configuration write or credential access was performed.

These checks do not validate an actual MCP, browser or desktop connection.
