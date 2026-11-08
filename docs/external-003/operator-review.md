# Local operator control review

Decision: **No remaining blocking finding for local decision recording.**
This is not approval to merge, activate dispatch or perform external actions.

One independent Sol 6.1/high reviewer examined UID attribution, private-state
checks, scope/spec binding, SQLite transaction and revision ordering, audit
snapshots, replay, expiry, revocation, re-enrollment, restart, concurrent decisions
and the absence of activation. This reasoning crossed the authentication,
filesystem and durable-state boundaries; routine Luna review was insufficient.
Luna workers implemented bounded CLI and behavioral tests. Requested model
selection was accepted; effective delegated identities are not independently
exposed. The lead completed its own source review and integrated the findings.

## Findings and corrections

- Writer contention could make an early clock sample stale before expiry was
  checked. The lead moved the sample after `BEGIN IMMEDIATE`. The reviewer
  independently held a real SQLite writer lock while expiry elapsed: the request
  was rejected, audit remained empty and current status remained missing.
- **P3/Low:** a JSON-valid large integer expiry raised `OverflowError` instead of
  the controlled protocol/CLI error. The boundary now translates it; a regression
  confirms no decision or audit write.
- Private leaf checks did not establish safe ancestors. The implementation now
  rejects other-owned or non-sticky writable ancestors before initialization and
  on each connection. The reviewer confirmed the narrow correction. Root/account
  owned sticky ancestors permit protected root/account owned child components.
- Two expiry tests initially allowed unrelated failure causes. They now use one
  frozen task and a starting clock after review time but before expiry. The final
  lock-wait test observes SQLite's write-lock attempt, advances the clock while
  the lock is held and asserts the specific expiry error. No timing sleep is used.
- The test worker found an unnormalized missing-directory error. It now raises
  `ProtocolError` and still creates no implicit state. An unused test import was
  removed after Ruff reported it; final static checks pass.

The reviewer confirmed the product corrections with five focused tests and the
separate actual-clock contention check. The lead/test worker confirmed the final
test precision corrections. No additional full review or native call was needed.

## Limits

The OS account and root are trusted; this is not human-presence authentication,
an OS sandbox or tamper-proof audit. No second-UID attack was run. SQLite opens
are path-based and rely on the enforced trusted ancestors and account ownership.
Supplied runtime fingerprints remain supplied observations, not fresh native
attestation. The decision journal is deliberately disconnected from dispatch.
Approvals do not start work and revocation does not stop already-running work.
Production use needs a reviewed account contract and tested dispatch integration.
