# Independent engineering review

Reviewer: delegated GPT Sol 6.1, high reasoning, read-only. Selected because the
patch combines identity/data isolation, credential forwarding, concurrent writes
and transport lifetime. Lead owns fixes, lifecycle and publication. STE
coding-code-reviewer instructions governed one review with concrete-fix followups.
No external review pool or recursive review was used.

## Findings and resolution

| Finding | Evidence | Correction | Verification |
|---|---|---|---|
| Medium: MCP request overtakes reconnect handshake | In-memory actual-client probe ordered initialize-start, tools-call, initialize-finish. | Every non-initialize send waits on the reconnect RLock through handshake. | Deterministic concurrency test; reviewer source confirmation. |
| Medium: MCP HTTP error body read ignores bounds | A .01s budget took .153s with a .15s error reader; real drip bodies could run indefinitely. | Close HTTPError without reading its body; retain status/error visibility. | Explicit no-read/close test; reviewer source confirmation. |
| Test gap: LinkAI unusual-role fixtures never exceeded limit | Fixture totals were below BUDGET1000 and bypassed trimming. | Assert over-budget precondition and double content; exact old/current state assertions. | Changed LinkAI file12 passed; reviewer checked meaningful precondition. |
| Medium: desktop mixed events still commit per item | Actual Zustand store with10alternating reasoning/delta pairs produced20commits in a frame. | Pending one-store-update folding and actual store regression. | Pending final desktop review. |
| Medium: valid secondary display window shrinks | 1800x1000 saved window on2560x1440 display clamped to1280x800 primary. | Preserve valid existing display bounds before recovery sizing. | Targeted geometry6 passed; final reviewer confirmation pending. |

Backend review is closed with no open finding. Cloud/config/SSRF, provider,
MCP service/tool-manager and fork authorization interactions were reviewed.
`findAgent` equivalence was checked: the prior helper also used exact ID lookup.
Language invalidation is supported by the existing App rerender plus lang prop.
Final desktop and complete combined-source regression results remain pending.

The reviewer ran only bounded read-only probes and diff checks. Fixtures do not
establish live provider, third-party MCP or physical display behavior.
