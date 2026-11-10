# PERSONAL-002 implementation and acceptance plan

Baseline: PR #9 remains open/draft at `adbe2105b0f45ab521429ba1427ac2887f7a2f97`.
All 22 PERSONAL-001 source/test hashes match its final validation manifest.
Branch `codex/bullgod-personal-002` starts from that exact head; the dependent
draft targets `codex/bullgod-personal-001` until the baseline is integrated.
No PR merge, live 9899 action or legacy maintenance is included.

## Design and ownership

- Lead: composition service/API/prompt integration, isolated launcher, actual
  endpoint/model/browser acceptance, docs, final regression and publication.
- Terra 6.1/high: `agent/memory/commitments.py`, necessary native transaction
  helper in ConversationStore and `tests/test_personal_commitments.py`. Atomic
  delivery, agent/session ownership and concurrent run state require integration
  beyond routine file implementation.
- Sol 6.1/high: narrow approved HTTPS JSON tool/transport, exact native policy
  registration and tests. DNS pinning, redirects and attenuated network authority
  require security reasoning; generic WebFetch must retain its existing boundary.
- Luna/high: article normalization/ranking/dedup module and focused tests.
- Luna/high: existing scheduler typed-action integration and focused tests.
- Luna/high: commitment UI/assets and Node behavior checks, separate from the
  existing PERSONAL-001 card. Lead owns shared script/template registration.
- One independent engineering review after integration; targeted re-review only
  for demonstrated findings. Full local regression on final executable source.

Commitments are owner-confirmed records in the same native conversation DB.
They hold objective, preferences, priority, status, source session/turn, an
explicit optional schedule, approved endpoint, follow-ups and pending decisions.
Temporary model thoughts and recovery-worker records are not commitments.
Owner mutation routes reuse authenticated console/origin/source checks.

The typed scheduler action carries an agent-bound commitment ID and schedule
generation. Native schedule metadata identifies the occurrence. SQLite claims
and unique occurrence keys stop overlapping/replayed deliveries; source rows,
seen/event state, rendered briefing and a native conversation message commit in
one transaction. An interrupted claim stays uncertain and visible, not successful.
Pausing/cancelling rechecks before fetch and before delivery. The next run and
catch-up policy use native scheduler timezone behavior.

The approved HTTP reader makes only bounded HTTPS GET requests to exact approved
endpoints, pins verified public addresses while retaining TLS hostname checks,
revalidates redirects and handles conditional caching/rate limits. It has no
credentials or write/publication power. The sandbox allows only the selected
model gateway and fixed loopback relays to approved pinned HTTPS addresses.
This adjusts the original direct-address plan to actual macOS sandbox rule
support. Remote text remains data.

Normalize source identity, URLs, publisher and all requested metadata. Rank from
owner topics deterministically, conservatively group related reports, and retain
source links. Compare substantive text rather than timestamps/headlines alone.
Record seen identities separately from delivered clusters and tracked follow-ups.
Return at most five relevant new/materially updated stories, never padding.
The native model can interpret the sourced briefing and explain outcomes; only
owner actions change durable intent. A LinkedIn draft is saved with sources and
claims, always awaiting separate publication approval; no publisher is added.

## Gates

1. API discovery: host ordinary GET, actual schema/body size/HTML/nulls,
   ETag/conditional result, observed limit support, no rate-limit stress; compare
   external-tool and isolated application access. Label unknown API guarantees.
2. Focused tests: HTTP/DNS/redirect/bounds/errors; normalization/dedup/updates;
   multiple commitments/preferences/source/isolation; native permission and
   guest/worker denial; atomic run/delivery, retry/uncertainty/restart; scheduler
   concurrency/timezone/pause; UI accessible labels/escaped text/stale responses.
3. One real isolated owner journey covers all 22 acceptance steps in the user
   specification. Use GPT-6 Luna through Pooler and a supported second model;
   actual endpoint data for live accessibility and clearly labeled fixtures for
   overlap/material updates/network failure/scheduler timing. Keep accepted
   interactions; restart only owned processes. Inspect actual browser rendering.
4. Independent source review; fix concrete in-scope defects. Then full guarded
   `scripts/ci_test.py tests/ -q` against frozen executable files, Node checks,
   and hosted CI if available without settings changes or runner investigation.
5. Publish README, exact receipts, limits and next capability; commit/push same
   named branch, draft PR, attach it and verify upstream 0/0 without prune/GC.

Completion requires the full owner experience and these gates. API access,
source correctness, local tests, hosted availability and deployment remain
separate claims. Existing PERSONAL-001 behavior/tests and all original evidence
are preserved. The live service stays unchanged.
