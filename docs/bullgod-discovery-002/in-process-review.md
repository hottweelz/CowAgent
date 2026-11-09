# DISCOVERY-002R independent review

Reviewer: existing delegated `discovery002_gate_a_review`, requested Sol 6.1 at
high reasoning. The interacting instance, caller and private-evidence authority
boundaries justify this assignment. The runtime does not separately attest the
effective worker model. The lead owns integration and publication.

Scope: the 002R changes after `cf4956df`, including the normal initialization and
reply hooks, initialized source, host factory, optional registry injection into
existing authority helpers and independent lifecycle tests. Existing unrelated
source was not re-reviewed. This is one review with bounded corrective follow-ups.

## Findings and corrections

| Finding | Correction |
| --- | --- |
| Cached model fallback and per-turn policy could change during enumeration without a config or caller-object change | Capture route and turn policy once, use the same policy for all candidates, and reject a changed final snapshot |
| A preexisting ambient parent run could be reported as a root reply when explicit lineage fields were absent | Capture the actual ambient parent before normal `_begin_run`; unproven parent lineage stays unknown |
| Explicit adapter observation did not validate a stale initialized owner before binding callback/contact | Validate the initialized runtime in `_bindings()` before any callback or contact; default host behavior is unchanged |
| Implementation self-review found `get_data_root()` could create a directory during authority observation | Use the same path calculation without directory creation only in the initialized registry path |

The reviewer confirmed that current process-global `conf()` is the execution
configuration source. Its validated type and coherent before/after digest allow
legitimate configuration updates. Registry replacement is valid only when the
actual owner/router relationships remain consistent and the snapshot is coherent.

The caller scope is object-bound and has a mutable liveness flag. `finally`
invalidates that flag before resetting the ContextVar, so copied execution
contexts cannot preserve an ended turn's authority. Reapplying or failing session
preferences invalidates the prior applied-state receipt. Cached caller routing
is reported separately from configured receiver routing.

Private filesystem ownership checks remain unchanged. The initialized factory
does not invoke the disk native snapshot reader or use native process metadata
to authenticate external proof. Its current journal reads still use the guarded
read-only journal path. No public endpoint, lazy initialization, memory content
access, dispatch or fallback to a weaker mechanism is added.

## Evidence boundary

The review can validate source and disposable tests. It cannot make the new
source available in the original PID. No supported authenticated ingress was
found, and that service has reload disabled. Without actual trusted live native
observations, the milestone must remain **BLOCKED**, not PARTIAL or PASSED.

**Final verdict: PASS, no remaining actionable findings.** The reviewer inspected
the frozen 20-case lifecycle file and independently parsed all six source/test
files with AST plus diff whitespace checks. The test worker reported 20 passing
cases and Ruff; the lead then passed 345 integrated focused cases. Exact hashes
and the local receipt are in [in-process-focused.json](in-process-focused.json).
The reviewer did not rerun pytest or access live state. Hosted CI remains a
separate publication gate.
