# Independent engineering review

One Sol 6.1/high reviewer examined false verification, attempt/contract fences,
authority boundaries and replay prevention. The review needed cross-component
reasoning about consequential success claims. It used private fixtures and ran
18 initial focused cases. No production service or provider was accessed.

The reviewer confirmed one P1 defect class: failed tool calls could return
before the durable gateway recorded them. With a pre-existing matching file,
a worker's success summary could then produce `completed / passed / confirmed`
despite a denied or empty Write call.

The fix records failures at the common stream result boundary, including
permission refusal, malformed/empty arguments and retry-protection refusals.
Calls rejected before execution have a nonmutating rejection receipt; an
existing failed tool receipt is reused. A receipt failure latches the attempt
guard. Direct gateway denials are also recorded. None of this converts a
rejected call into a side-effect intent.

The lead also preserved file-broker permission-denial metadata in ordinary tool
receipts, so denied reads cannot disappear during failure-record de-duplication.
A direct native Read of a fictional private file is denied, its content remains
hidden, and acceptance fails even when the public artifact matches. A separate
injected verification-journal failure leaves completed execution unverified
with an explicit error; a later read-only check can recover the report.

Regression evidence uses actual Agent streaming and native tools. The denied
write, empty arguments, malformed JSON and invalid content cases all preserve
completed execution and a matching file, but fail acceptance. Filesystem state
can independently remain confirmed. Incorrect generated artifacts fail both
acceptance and confirmation. Worker claims cannot change either verdict.

The reviewer found no other actionable defect in the bounded pass. The lead
implemented and verified the remaining failure-path fixes. No second broad
review or independent final approval is claimed.

Other checks cover report persistence and history, stale attempt/contract
fences, missing/unsupported checks, private-path denials, explicit read-only
re-verification, and real process death after execution completion. Restart
finishes the missing verification without another worker attempt or write.
