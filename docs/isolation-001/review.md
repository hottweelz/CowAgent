# Independent engineering review

One read-only Sol 6.1/high review inspected the implementation against the full
ISOLATION-001 brief, including the explicitly allowed restricted-mode alternative.
The reviewer independently ran the then-current focused suite (37 passed) and
used disposable execution reproductions. No production data or services were used.

| Finding | Reproduction and impact | Resolution and execution evidence |
| --- | --- | --- |
| P1: host state remained writable | A child with an explicitly shared owner root wrote scheduler/tasks.json. TaskStore loaded the task; a fake scheduler bridge received full-access execution mode. Private run traces were also readable. | Agent.protected_paths now retains absolute host-state subtrees and the file broker rejects reserved state segments. `test_child_cannot_plant_scheduled_work_or_grant_private_state` proves no task is inserted and private-root regrant fails. The private-state test covers runs, scheduler, templates, system/users and backups. |
| P1: APFS case alias bypass | A protected PrivateSibling directory was readable using a differently cased spelling on this host's case-insensitive filesystem. | Denied paths and host-source protection use conservative Unicode-normalized, case-folded comparisons. Root grants still use exact descriptor-relative walking. `test_private_path_case_and_unicode_aliases_fail_closed` tests actual alias read/write attempts. |
| P1: receiver exclusions lost in delegation | A target with an ancestor shared project could read source/private.txt because only caller exclusions were present and the child used source identity. | Build the receiver authority using target identity and its own excluded sibling workspaces, then intersect and retain both exclusion sets. The execution identity remains the target. `test_receiver_keeps_its_exclusion_for_source_private_workspace` runs real delegation, streaming and native Read; the fictional secret never reaches a target model request. |

All three findings are fixed in the delivered source. The final focused suite
has 40 passing tests and the integrated selection has 1,294 passing tests with
15 documented platform/opt-in skips. These counts include the regression cases.
The lead verified the fixes; a second broad review was not performed. The reviewer
delivered findings and completion notice, but its final tool status was an
automated content flag; no independent final approval is claimed.

Residual boundary: trusted host code brokers restricted operations. It does not
contain malicious installed Python or arbitrary external programs. Those worker
execution mechanisms remain denied. The macOS prototype is evidence for the
remaining design work, not a shipped sandbox or a claim that macOS isolation is
impossible.
