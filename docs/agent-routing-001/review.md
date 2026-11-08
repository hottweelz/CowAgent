# Independent review and verification

2026-11-08. Codex owns lifecycle and integration. One Sol 6.1/high reviewer
examined the private-memory, approval and recovery boundary because those
interacting security contracts required stronger reasoning than routine Luna
work. A separate Luna/high verifier checked the retained real result.
Requested model selections were accepted; effective delegated identities are
not independently exposed by the collaboration runtime.

## Engineering review

No remaining blocking finding for this controlled one-task scope.

Corrections made before the real run:

- Reject config-level MCP startup as well as workspace `mcp.json`.
- Check scheduler backup files because native startup can restore them.
- Preserve ordinary provider agent/session/channel metadata.
- Reject an engaged fallback, including another provider with the same model
  name; derive reported provider from the observed primary route.
- Normalize malformed model output to a generic error. Never export raw model
  responses or `JSONDecodeError.doc`.
- Require exact expected-report equality before publication, followed by
  independent artifact verification.

The final supplemental review covered the bounded CLI and caller/native split.
No model runs or accepted tests were repeated for review. The product keeps
the existing native `agent_delegate` isolation behavior unchanged.

## Independent result checks

The verifier read only the permitted fictional task/report, safe receipt,
operator journal metadata and repository source. It did not read the native
workspace, native config, launch secret or raw runtime logs.

- Seven input records: four accepted; exceptions at indices 4 (duplicate),
  5 (void), and 6 (invalid refund sign).
- Independent sums: paid 20,000, refund -2,000, pending 3,000, net 18,000 cents.
- Exact artifact match and SHA-256
  `a69068c8b3daa395b9a86aaf37e70a1b9d741c28c934253281bf9c6dbd9b8d91`.
- Enrollment/discovery match: registered `testpilot`, configured
  `nvidia/nemotron-3.5-super-vl:free`, provider `custom`.
- Independently recomputed executable-source fingerprint matches enrollment.
- SQLite metadata confirms exactly one submit, native and publication intent,
  all bound to task `4bb04826-e64e-43d4-9c4c-a010777786eb`.
- Native intent and completed result share session
  `f96a59e3-108e-4b06-9ac8-55cebf1aac79`.
- Enrollment/task approval revisions are both 1. Acceptance source requires an
  unapproved submission to fail before writing the task approval.
- The caller reports zero private-open attempts. The audit hook covers Python
  `open` calls; it is not OS isolation and no blocked attempt was needed.

The safe published receipt includes native start/completion log metadata bound
to the same session and run. Provider identity is supported by native discovery,
unchanged postflight fingerprints and the successful post-run source guard;
it is not an independent attestation from the remote provider. The exported
result intentionally has a smaller metadata set than the native runtime.

## Verification bounds

The 163 focused checks and one actual authenticated task satisfy this milestone.
No fresh full-regression, UI interaction, live-crash campaign or hostile
same-account isolation test is claimed. Crash/restart/revocation cases use
focused fixtures and the unchanged approval/recovery contracts. Native memory
maintenance remains runtime-owned. The experiment service has exited.
