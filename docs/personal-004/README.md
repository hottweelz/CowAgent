# PERSONAL-004: optional registered specialist research

Published for review as draft [PR #12](https://github.com/hottweelz/CowAgent/pull/12)
against integrated master. Implementation commit: `797f323e`.

[Final integration review](integration-review.md): PASS on source head `f52e89f1`,
with hosted CI unverified and production deployment separate. PR remains draft.

BullGod retains the owner's identity, goals, memory and conversation. It can
recommend a registered specialist for a concrete sourced question. The owner
reviews the exact input, approves one request, and separately starts execution.
BullGod receives a verified source excerpt and classification, explains the
limits, and keeps working when no specialist is available.

The isolated real-model acceptance used **GPT-6 Luna through the existing local
Pooler**, both for BullGod and the new registered NewsAnalyst fixture. No local
model download was needed. This does not deploy the feature to live CowAgent.

## Integrated baseline

PRs [#9](https://github.com/hottweelz/CowAgent/pull/9),
[#10](https://github.com/hottweelz/CowAgent/pull/10) and
[#11](https://github.com/hottweelz/CowAgent/pull/11) were merged normally, in that
order, after the required-condition and retained-evidence review. Each merge
has the exact tree of its reviewed head. The final master is
`ab13b789e28e3efc8571e6406acda8c88e914b77`; this branch starts there.

The repository had no required status/review rules, unresolved review threads,
or head checks. Hosted execution was unavailable; an empty check list was never
reported as a pass. No workflow, protection or Actions setting changed. Original
branches, commits, reports and deferred PRs #4–7 remain preserved. See
[integration evidence](integration.json); its nested PR objects are the recorded
**pre-merge** snapshots, with separate successful merge receipts.

## User experience

1. Save a news commitment and explicitly authorize its configured read endpoint.
2. Check the source. Ask BullGod whether one delivered development warrants help.
3. In **Personal commitments → Optional specialist research**, select a
   registered target, delivered sources and one question. Inspect the exact
   source snapshots and allowed output before approving.
4. Approve the concrete request, then use **Run approved research once**.
   A read grant or generic specialist suggestion alone cannot authorize it.
5. Read the verified findings and BullGod's explanation in the owner conversation.
   The result remains linked to the commitment after restart and in later chats.
   Earlier requests can only be changed from their original conversation.

This first action class is deliberately small: a specialist evaluates supplied
source snapshots and returns exact excerpts, relevance and priority. It cannot
browse, fetch full articles, import new material, publish, or use other tools.
The existing authenticated fictional-record adapter and generic restricted
`agent_delegate` keep their original contracts.

## Implementation and compatibility

| Files | Responsibility |
| --- | --- |
| `agent/personal/collaboration.py` | Additive `personal_research` ledger in the native ConversationStore DB; immutable source/target binding; owner review; durable single-use claim; native target session; strict output verification; atomic result and owner message. |
| `agent/personal/commitments.py` | Compose collaboration state and three operations into the existing authenticated owner API. Existing origin, agent and source-turn checks remain. |
| `agent/protocol/agent.py` | Optional empty tool-schema override for native system-prompt construction. Ordinary callers retain existing behavior. |
| `agent/memory/personal_context.py` | Refresh available specialist metadata and bounded research history each owner turn. Existing guest/restricted-runtime exclusions remain. Explain supported capabilities and source limits. |
| `channel/web/static/js/chat/commitments.js`, `channel/web/static/css/commitments.css` | Inspect, approve, deny and execute; accurate terminal states, original-chat navigation, source links and readable status badges. |
| `common/model_defaults.py`, `scripts/bullgod_dev.py` | Select the newest supported numeric version within a requested model family for new unpinned developer instances. |

The executor resolves the registered target through native `AgentBridge.get_agent`
with its own host identity, fresh session, native persona, memory manager and
configured provider/model. It assembles that runtime's system context and calls
its native streaming model. It does not copy the target's private memory into
BullGod or replace the target with a generic worker. There is no second registry,
agent engine, scheduler, dispatcher or migration controller.

Before initialization, metadata checks reject overlapping registered workspaces,
escaping private-context paths and hard-linked private files. No private file
contents are inspected by this check. The intended shared conversation database
still uses native agent/session namespaces. Profile/model/workspace binding is
checked again before the model and before successful delivery.

An execution claim commits before initialization/model work. Concurrent and
repeated requests reuse its state. Failed and uncertain requests do not replay.
A new service process marks abandoned claims uncertain. Native task/reply history
is saved in the target-owned session and synchronized with its cached runtime.
Only known source IDs, exact supplied substrings and fixed classification values
can return to the owner; arbitrary prose or extra fields are rejected.

## Model selection

New developer instances with `--model-base` and no `--model` default to the
newest entry in the repository's supported catalog for `--model-family` (Luna
by default). Numeric versions are compared numerically, including 6.10 versus
6.9. The present catalog selects GPT-6 Luna and GPT-6.1 Terra/Sol. There is no
inference that a newer model exists upstream but is absent from this catalog.

An explicit model pin remains explicit. GPT-5.6 is available only when explicitly
selected as a last-resort fallback. The generated instance disables automatic
model fallback; an unavailable route does not silently downgrade. Existing
registered agents retain their configured model and are not rewritten.

## Actual acceptance

A fresh private instance on **19894** retrieved actual HTTPS news from
`https://tyl.ee/api/news`. BullGod recommended a bounded review of a reported
Mercado Bitcoin incident. The selected feed snapshot contained only a headline;
this was stated in the approved question and in the final owner explanation.
No claim of full-article research or independent publisher verification is made.

The new isolated registered `news-analyst` profile was not a copy or
impersonation of production TestPilot. One approved research request ran with
GPT-6 Luna, its own native persona and synthetic memory, a fresh native session,
and zero tools. Runtime-only observations confirmed that its context contained
its own synthetic marker and lacked the owner's synthetic marker. Only booleans
and identity metadata were recorded by that observer.

The pending and denied request made no model call. The completed request returned
an exact source excerpt with relevance/priority. Repeated execution and a process
restart left the same receipt, message and single specialist call. A new owner
conversation retained read-only research history and an original-chat link.
Disabling only the disposable specialist demonstrated unavailable selection and
BullGod's direct continuation with the commitment and separate Cedar goal intact.

An initial BullGod response suggested a nonexistent full-article workflow. That
response is retained. Explicit capability guidance corrected it; same-session
and fresh-chat explanations now distinguish snapshot analysis from manual source
review. No accepted specialist interaction was replayed to regenerate evidence.

## Verification and evidence

- [Independent engineering review](review.md): five concrete findings fixed;
  identity, authority, history and output boundaries reviewed.
- [Local regression](local-regression.json): **6,210 passed, 36 skipped, 93
  subtests passed**. The run overlapped the seven-line capability-guidance update;
  final-source context tests then passed **5/5**. A later CSS text-color fix was
  checked in the real screen. Both deltas and final hashes are explicit.
- Focused integration: **44 passed**, plus Node UI checks. Changed Python syntax,
  Ruff F, JavaScript syntax and Git whitespace checks passed.
- [Native receipts](native-validation.json), [runtime source binding](runtime-source.json),
  [independent acceptance audit](acceptance-audit.json) and
  [preservation receipt](preservation.json).
- [200% UI evidence](ui-validation.json): no horizontal page overflow, visible
  composer/send control, keyboard scrolling and original-chat navigation;
  final status-badge contrast measured from actual computed colors.
- [Owner continuation](owner-continuation.png) and
  [200% research history](research-200-percent.png).

The local suite, native runtime acceptance, hosted CI and production deployment
are separate claims. [Publication evidence](publication.json) records empty checks/statuses and workflow
runs on the implementation commit, not a hosted pass. No
production activation or live CowAgent upgrade was performed.

## Isolated development and retained limits

Use the existing [isolated launcher procedure](../bullgod-reset-001/README.md).
For the tested gateway, select `--model-base
http://127.0.0.1:4000/backend-api/codex`, `--model-family luna`, a separate port,
and the explicit project virtual-environment Python. Omit `--model` to exercise
the newest-supported default. The launcher consumes the existing gateway
credential in memory at start; do not print, copy or store its value in fixtures.
The console credential, workspace, agent profiles and conversation data are
separate. The only approved external data endpoint in this acceptance is the
news endpoint above. All diagnostic probes were task-owned, observed the native
path without changing responses, and were removed from startup after acceptance.

The one-shot action follows the native single-writer-process contract. Transport
timeout is not universal hard cancellation. Filesystem metadata checks assume
that the same local user does not replace paths concurrently during initialization.
There is no hostile same-user or packet-capture isolation claim. Source verification
checks provenance, not truth, completeness, significance or model judgment.

Next product work should improve BullGod's ordinary owner experience and real
source coverage. This milestone needs review of its draft PR before integration;
legacy service maintenance is not a product-development prerequisite.
