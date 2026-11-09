# FIRST-BOOTSTRAP-002 implementation and qualification plan

Start from published PR #6 fcbc0d25. Preserve the dependency chain and live
checkout. No live process control, firewall change, backup of private contents,
ownership change, authority refresh, model/provider execution or merge.

1. Reconcile baseline and selected current metadata. Reuse established facts
   unless they can drift or the new decision needs stronger evidence.
2. Qualify a reversible external admission boundary in disposable processes.
   Test chat, streaming, queued routes, in-flight work, health, bypass and restore.
   A proxy with a reachable direct listener is not an enforced legacy boundary.
   An untested OS rule is not evidence. Report any remaining Class C condition.
3. Map and instrument the seven actual plugins, preserving behavior/authority.
   Account for constructors, callbacks, child threads/futures and external work.
   Positive coverage requires explicit known implementation; unknown detached work
   retains fail-closed protection. Terra owns plugin code/tests and evidence.
4. Implement a private, opt-in, process/epoch-bound operator drain control. Reuse
   the existing OS-account/private-file trust boundary and genuine initialized
   owner. No public route, target-PID selector, model tool, signal, cancellation,
   or automatic reopening. Sol owns control module/CLI/tests; lead owns startup
   integration. Requests and sanitized receipts are one-use and durable.
5. Map actual data/schema/file ownership and qualify an expanded fictional
   four-database checkpoint/restore with file manifest, modes/symlinks, unknown
   files, corruption/missing-entry rejection and no effect replay. Luna owns this
   evidence/fixture unit; actual private data copies remain separately authorized.
6. Integrate real enabled-plugin startup with operator control and recovery in a
   private disposable process. Freeze executable source. Run focused integration,
   full protected local directory regression, exact-source hosted matrix and one
   independent high-reasoning review. Fix concrete findings and rerun affected gates.
7. Publish docs/first-bootstrap-002/README.md with twelve answers, one concrete
   bounded policy candidate, technical controls vs owner decisions, exact source
   and evidence, and either Class B conditional GO or justified Class C NO-GO.
   Draft PR targets codex/first-bootstrap-001; verify named upstream 0/0.

Checks carried from lessons: source-mode plugin state follows CWD; fixture leases
are not native model tasks; preserve real legacy uncertainty; four DB roles include
shared default conversation/memory; no raw live SQLite copy; exact source restore
must cover index additions and preserve unrelated state; bind new control only to
its initialized owner; freshness and replay checks precede closure; timeout keeps
admission closed and never cancels work. New runtime code requires fresh CI.
