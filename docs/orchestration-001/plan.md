# ORCHESTRATION-001 audit plan

Baseline: `master` at `c2c39a2e`. Work only on
`audit/orchestration-001-native`. No implementation changes, production
configuration/credentials, external services, self-evolution, PR or merge.

1. Two read-only Luna/high workers map (a) native identity, delegation,
   concurrency and persistence, and (b) permissions, memory/skills/workspaces,
   approval, verification and external-runtime integration. Lead integrates
   source evidence with exact file/line references.
2. Lead adds a reproducible audit probe under this directory. Use a fresh
   disposable workspace and synthetic streaming model responses; keep the real
   Agent loop, delegation tool, worker builder, tool execution and SQLite store.
   Exercise two-worker overlap, independently checked fictional artifacts,
   provider failure, cancellation/timeout, process death/restart, and attempted
   out-of-scope worker actions. Clearly identify every substituted boundary.
3. Run the existing focused native orchestration/permission/persistence tests.
   Preserve negative results as findings; do not fix implementation during audit.
4. Write README.md and sanitized receipts covering every investigation and
   controlled-test requirement. Compare BullGod against the capabilities stated
   in this brief; no separate BullGod specification is present in the checkout.
5. One bounded evidence review, scope/preservation checks, handoff and commit.
   The dedicated branch has no upstream; do not invent one or open a PR/merge.

Acceptance is evidence for what works and what fails, not a requirement that the
architecture pass every supervisory need. Source claims, controlled behavior,
inferences and untested live-provider/runtime integrations stay distinct.
