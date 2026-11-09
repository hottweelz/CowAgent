# Independent engineering review

The independent Gate B review concluded **PASS** after four concrete findings
were corrected. The reviewer reported no remaining actionable source finding.
This verdict covers the implementation and fixture evidence. It does not certify
current live enrollment, proof or admission.

The assigned reviewer was `discovery002_gate_a_review`, requested as Sol 6.1 at
high reasoning. Cross-component authority, HMAC provenance, SQLite read-only
semantics and accidental dispatch justified this assignment. The runtime accepted
the requested model parameters; it did not provide a separate effective-model
attestation. One review and bounded corrective follow-ups were used.

| Finding | Correction and regression |
| --- | --- |
| A disabled profile could abort all native candidate enumeration | Inspect disabled profiles without requiring enabled state; deny that candidate independently |
| A negative availability observation could remain valid indefinitely | Timestamp and expire unsuccessful observations within 30 seconds; stale negative evidence becomes unknown |
| Current native state did not establish the running adapter's full approved enrollment | Compare the current snapshot and the authenticated fingerprint of the entire frozen enrollment, including its probe digest; a new approval cannot update an old process binding |
| An authentic historical focused receipt could overstate its source coverage | Require a complete tested-source fingerprint that matches the approved and current source; partial source maps remain insufficient |

The initial integrated focused run passed 350 tests, including 27 trusted-reader
cases and 21 independent acceptance cases. See [that receipt](focused-before-ownership-fix.json).
Positive fixtures use disposable authority and an actual authenticated temporary
adapter inspection; they are not evidence of current live target eligibility.

The final live check separately exposed an environment trust limitation: the
actual config path has a group-writable ancestor. The strict reader rejected it
before selection. The guard remains intact; no filesystem permissions, live
configuration, approval or credential was changed to make acceptance pass.

The production worker independently traced the supported interfaces after this
failure. It confirmed that private binding/state observations can proceed without
reading config or proof files, but full trusted selection remains BLOCKED. No
registryless selection mode exists. Public service metadata and unchecked native
file readers are not valid fallbacks for the rejected trusted source.

Known limits remain explicit: native isolated proof and coherent free capacity
have no authoritative current source; safe Codex executable attestation is
unavailable; retained real enrollment and task approvals are expired. These
conditions must not be promoted into verified eligibility.

## Ownership-enforcement correction

Further actual filesystem inspection found APFS ownership enforcement disabled.
Changing mode bits alone would not establish owner trust, so the pending
mode-only permission request was withdrawn without changing the host.

The same independent reviewer checked the bounded correction and returned
**PASS, no remaining actionable finding**. The Darwin structure matches Apple's
installed SDK (2,168 bytes, flags offset 64, mask `0x00200000`). Independent
metadata-only `statfs64` and `fstatfs64` calls agreed: the workspace volume is
rejected and ownership-enforced private temporary storage is accepted. Python
`statvfs` masks the needed flag and is not used as authority.

The helper retains existing mode/owner/symlink checks, rejects ignored ownership
or unavailable Darwin APIs, blocks operator initialization before writes, and
leaves recovery admission unknown. Linux does not load the Darwin API. No
subprocess, network, mount or permission change was added. The worker passed 107
targeted tests; the lead then passed 356 integrated tests (33 reader cases and
21 independent acceptance cases). Fresh hosted validation is recorded separately.
