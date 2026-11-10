# PERSONAL-001 reproducible owner scenario

Use a fresh instance from the [launcher procedure](README.md#separate-development-with-the-pooler).
This procedure requires an available model endpoint and explicit permission to
use it. The recorded run used the existing loopback Pooler, GPT-6 Luna and a
GPT-5.6 Luna comparison. Do not copy production profiles or authority records.
Keep the launcher parent environment's system TMPDIR; the launcher gives its
child a private TMPDIR. Select `responses` in the new instance's config before
starting this Pooler setup. Never display that config or the credential value.

Open the instance's printed console URL (19892 for the recorded run), sign in
with its disposable password, and use these fictional inputs. A manual browser
run is sufficient. For automation, use one Playwright lifetime and a separate
persistent browser profile inside the instance root. Close the browser before
the Playwright lifetime ends.

| Step | Owner interaction | Required observation |
| --- | --- | --- |
| 1 | Tell BullGod: “Help me prepare a brief Cedar workshop plan and draft checklist before Friday. The venue capacity is still undecided. I prefer brief workshop plans.” | Natural response from the BullGod profile; native history usage identifies the selected model. |
| 2 | Save that goal, pending venue decision, next action and plan-style fact through the continuity card. | Records cite the actual owner message, including sequence zero where applicable. |
| 3 | Close the test browser; stop/start only this root using `bullgod_dev.py`. Reopen its saved conversation. | Identity, transcript, goal, pending decision and fact remain. No action starts automatically. |
| 4 | Ask what matters and what to do next. | BullGod retrieves the saved workshop context and proposes a bounded useful next step. |
| 5 | Inspect the continuity card's tools, skills and permission state. | Available runtime capabilities and current authorization limits are shown. Before runtime initialization, unknown/unloaded is expected. |
| 6 | Select another available model in the native model chooser, then ask about the saved goal. | Native request metadata shows the changed model; profile, session ownership and goal remain the same. |
| 7 | Correct the fact to “The owner prefers detailed workshop plans.” Ask for the **exact current saved preference**, distinguishing the particular goal's brief format. | The current fact is retrieved; its source and update time are inspectable. The unchanged goal and old transcript remain separate. |
| 8 | Ask for a short checklist in one fenced text block, then create a proposal for `projects/cedar/checklist.md` using its exact content. | A pending proposal exists; the file does not. An authenticated JSON `execute_action` POST before approval returns 400. |
| 9 | Review path/content and select **Approve and execute once**. | One completed record, native readback verified. Independently read the fictional workspace file and compare its bytes/digest with the proposal and result. |
| 10 | Save progress that the checklist was created and verified; keep the pending venue decision. | Goal revision advances once and the action result remains linked to the conversation. |
| 11 | Ask what actually happened, where the file is, and which decision remains. | Natural explanation matches the recorded result and pending decision. |
| 12 | Forget the plan-style fact and open a fresh conversation. Ask whether a current plan-style preference is saved. | No active fact remains; the model does not report the forgotten fact as currently saved. Original transcripts remain retained. |

Finally, restart the owned service again. Confirm one completed action, unchanged
file bytes and modification time, unchanged goal revision, and HTTP 400 for a
duplicate execute request. Stop the owned service and close the test browser.
Preserve the disposable root when retaining evidence; create a new root for a
new acceptance run instead of silently replaying old action IDs.

HTTP observations use the authenticated console session and
`/api/personal/<session_id>?agent_id=bullgod`. Mutations are JSON with an explicit
`operation`. Do not send authorization in a query string. The native history
endpoint supplies per-request `model` and `requested_model`; these prove routing
metadata, not an independent attestation of the provider's model internals.

The [recorded result](native-validation.json) preserves partial-helper failures,
the ambiguous model answer, subsequent evidence, final asset overlay and cleanup.
It represents one continued owner journey, not a successful single invocation of
the [historical partial helper](reference/acceptance-attempt.py.txt). That helper
is reference evidence and must not become an active maintenance dependency.

For a future clean run, use a fresh snapshot of the final source; no browser
asset overlay is needed. The quote-boundary regression can be checked locally
with `node channel/web/tools/check-personal-ui.mjs` without another model call.
