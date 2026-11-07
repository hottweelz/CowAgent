# EXTERNAL-002 plan and gates

Final status: **BLOCKED at CODEX-CAPABILITY-001**. See [README.md](README.md)
and [runtime-gates.json](runtime-gates.json). This plan is retained as the
ordered acceptance contract; steps after the capability gate remain unfinished.

Task branch: `feat/external-002-codex-adapter`. Fork master remains `e642eec1`.
The published EXTERNAL-001 dependency `bfd64e39` is a direct descendant of that
baseline and was fast-forwarded into this dedicated development branch. Its
report blob matches GitHub and all retained evidence remains in the tree.

## Mechanism selection

Installed Codex CLI is 0.165.0. Authentication reports ChatGPT. The selected
model/provider/effort belong to Codex and will not be overridden. Existing
model/provider/authentication configuration and credentials will not be
rewritten or copied. Codex's native fixture-project trust entry was later
removed with an exact-original-hash check; the report records that side effect.

`codex exec --json` is the smallest scripted interface, but its documented
signal semantics do not prove descendant termination. It also lacks the
per-thread named permission-profile selection required when the existing
configuration includes legacy full-access sandbox settings. The documented
app-server stdio API is the narrowest candidate that provides explicit profile
selection and `turn/interrupt`. It is beta and must be version-pinned and
checked against the installed generated public schema. No internal rollout
files, undocumented API, TCP listener or shared live app-server is used.

The independent architecture review identifies a hard boundary: model-driven
shell/program execution can detach descendants and invalidate the inherited
termination contract. The candidate design therefore requires native file
editing only, supplies frozen fixture file context, disables model shell and
alternate execution/service surfaces, and declines every escalation. This
does not enable arbitrary commands in CowAgent restricted workers.

## Ordered implementation

1. Verify branch ancestry and published dependency; inspect installed CLI and
   official documentation. Completed foundation integration is branch-local.
2. Prove the effective profile, model preservation and excluded tool surfaces
   before any real task. A command sandbox probe alone does not prove native
   file-patch confinement; probe native patch separately with owned canaries.
3. If these gates pass, implement the versioned adapter with durable task and
   native thread/session/turn references, structured progress, approval,
   duplicate suppression, result and cancellation state. Persist intent before
   native task submission; unknown dispatch never causes automatic replay.
4. Keep successful transport, runtime execution, task termination, acceptance
   and independent state confirmation separate. A transport loss must not be
   mapped to a terminal state that asserts termination.
5. Exercise a real code edit, host restart, duplicates, unavailable Codex,
   cancellation during real execution and uncertain-effect reconciliation in
   disposable Git repositories. Do not mutate production CowAgent state.
6. Product verification stays read-only native artifact checks. Controlled
   behavioral tests may run only after edited fixture bytes equal an exact
   trusted source/hash fixed before delegation; never import model-modified
   tests, hooks or arbitrary source into an unrestricted verifier.
7. Independent security/architecture review, full retained Python/UI gates,
   strict renderer/build, report/receipts, handoff, commit/push and 0/0 sync.
   No master merge or activation. If the real runtime cannot meet the security
   contract, publish the exact blocked gate and do not weaken the boundary.

## Evidence so far

- CLI/schema inspection and official docs support named profile selection in
  app-server `thread/start.permissions`, with `activePermissionProfile` in the
  response; model/provider were omitted and returned unchanged.
- Minimal profile without explicit root/temp denial allowed a disposable
  outside canary under `/tmp`. The documented workspace-only profile with
  explicit root/temp denies allowed workspace read/write while denying outside
  reads/writes and symlink reads. No real credential was probed.
- Configured MCP metadata can remain listed after disable overrides. Count
  alone is not proof of callable tools. Effective configuration/runtime status
  and native patch/cancellation evidence remain required before acceptance.

## Ownership

Codex lead owns lifecycle, policy gates, integration, evidence and Git. Luna/high
researches the official interface. One Sol 6.1/high reviewer checks approval,
authentication, profile enforcement and task/effect lifetime across processes;
this cross-boundary reasoning exceeds a routine Luna review. Further bounded
engineering assignments covered the foundation only: Terra 6.1/high owned the
stdio client because concurrent response/event and process cleanup boundaries
needed more than routine edits; Luna/high owned isolated policy tests and the
release gate rerun. No worker registered or activated a real adapter.
