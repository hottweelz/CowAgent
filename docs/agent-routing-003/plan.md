# AGENT-ROUTING-003 plan

Extend the existing persistent named-agent adapter to registered `testpilot`
and `testpilot2`. Keep native profiles, instructions, model routing and memory
ownership. Use existing authenticated IPC, operator approvals, task journals and
exact analysis-output verification. Keep native `agent_delegate` unchanged.

1. Resolve the four scheduling-fixture failures before adapter implementation.
   Luna owns `tests/test_parallel_tool_calls.py`. Reproduce the failures, use a
   real registered tool and valid read-only Agent context, and retain the real
   authorization check. Gate: all six file tests and the recorded five-file
   selection pass. Completed: 6/6 and 60/60 passed.
2. Extend target selection and execution checks. Terra 6.1 owns the four
   `agent/external/cowagent_*`/`operator_review.py` files and three CowAgent test
   files. It is selected for integration across authentication, mutable native
   session state, memory ownership and concurrency. One enrolled target per
   process; runtime credential and approval bind that target. Same-runtime work
   is serialized; separate target runtimes may overlap. No caller-selected
   prompt, model, memory path or old session.
3. Check actual memory manager paths against the selected profile and reject
   target workspace aliasing. Return only public identity, model, profile hash,
   opaque memory-scope digest and native run/session/process/timing metadata.
   Retain exact safe-output and provider-fallback gates. Permit settled recovery
   history but reject rows that startup could resume or verify.
4. Lead owns a bounded paired acceptance client under this directory. Use one
   fixed fictional dataset per target, independent credentials/enrollments,
   journals, sockets and exports. Launch native Unix-socket processes only;
   preserve the existing webserver. Independently check arithmetic, ownership
   metadata and one durable submit/native/publication intent per task. Claim
   parallel execution only if native run windows overlap.
5. Run focused adapter/approval/registry/routing regression and static checks.
   Obtain one independent engineering review of identity, privacy, authority and
   concurrency boundaries, then validate each target once through the real
   authenticated adapter. Fix concrete findings; do not replay valid model work.
6. Record evidence, limitations, handoff and durable project facts. Publish
   `codex/agent-routing-003` to the existing origin and verify upstream 0/0.
   No master merge or persistent service activation.

Acceptance: both registered targets return independently correct reports under
their own native instructions, memory managers, configured models and fresh
sessions. Invalid target/credential/enrollment/receipt bindings fail closed.
Parallel target runs have separate mutable runtime state and durable receipts.
No client access to private memory contents. Existing server and unrelated files
remain intact. Ordinary native bookkeeping may write its own indexes/journals.

Lessons applied: trace actual storage ownership; do not use display run ownership
or a model's self-name as identity proof. Preserve unknown execution outcomes;
never retry them automatically. Check scheduler backups and pending recovery
before native startup. All fixture tests use private temporary configuration.
