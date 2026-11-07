# Independent security and architecture review

Date: 2026-11-07. Reviewer: delegated Sol 6.1/high, read-only.
The stronger reasoning assignment covered authentication ownership, native
permission profiles, approval and uncertain effects across process boundaries.
The parent owns integration, handoff and Git. No recursive review was used.

**Decision: BLOCKED.** Publication of the inactive foundation and findings is
supported. Production use, merge and a complete real-adapter claim are not.

## Blocking gate: CODEX-CAPABILITY-001

Structured native `additional_tools` metadata advertised `spawn_agent`,
`followup_task` and other collaboration tools despite `multi_agent=false` and
`multi_agent_v2=false`. The intended file-only execution boundary is unproven.
No collaboration call or escape was demonstrated. Configuration flags and a
prompt instruction cannot establish that those operations are unavailable.
The origin of the extra advertisement is not established by this review.

Before any further real task, require a supported control or authoritative
matching-runtime implementation that establishes rejection of all excluded
worker mutations. Do not enable shell, change provider/model, or invoke an
unbounded worker to test around the gate. Keep the current native authentication.

## Closed finding: same-group process cleanup

Severity: P2. Initially, `CodexClient.close()` skipped process-group cleanup
after the leader had exited. A same-group child could keep stdout and the
reader thread alive. The reviewer reproduced this with a fake process and
cleaned the owned group.

The correction performs bounded TERM/KILL group cleanup even after leader exit
and makes close idempotent. Independent narrow confirmation passed both cleanup
tests, with five unrelated cases deselected. `git diff --check` passed. The
full final regression includes the corrected seven client cases.

This closes the reported same-group defect. Descendants that detach from the
group remain outside the guarantee. Process exit or a native interrupted turn
must not be represented as confirmed effect quiescence without further proof.

## Other reviewed boundaries

- `attest_configuration()` now names its actual scope: settings checks do not
  approve execution or certify the model-facing tool surface.
- Native fixed-command sandbox canaries do not prove native patch confinement.
  An eventual adapter needs outside-root, symlink and protected-file patch tests.
- The documented native Code Mode host may be used as a candidate interface,
  but its actual tools and cleanup must be checked. No pure-V8 hard-isolation
  claim follows from the inventory result.
- A transport timeout or EOF cannot map to a terminal EXTERNAL-001 state that
  implies termination when effects may remain active. No uncertain replay.
- Running arbitrary model-edited tests or imports in a verifier would execute
  untrusted code. Controlled behavioral tests require exact trusted source
  bytes fixed before dispatch and a private read-once snapshot. Product
  verification remains declarative and read-only.
- No configuration/auth/model write or approval-accept path was found in the
  reviewed foundation. Codex's native disposable-project trust side effect and
  the parent's exact-hash restoration are separately recorded in the runtime
  receipt; they are not attributed to a policy-helper write.

## Scope and limits

Reviewed the proposed execution boundary, supplied official schemas and probe
receipts, `codex_client.py`, `codex_policy.py` and focused client tests. The
reviewer made no source edits and ran no real Codex/model task or collaboration
probe. The process regression used fake child processes only.

Native patch confinement, successful real coding and behavioral tests, durable
Codex task identity/idempotency, active restart, actual cancellation with
confirmed quiescence, and exclusion of alternate execution capabilities remain
unverified. The event queue is unbounded; no general containment or other
platform guarantee is established. See [README.md](README.md) and
[runtime-gates.json](runtime-gates.json) for the deployment boundary.
