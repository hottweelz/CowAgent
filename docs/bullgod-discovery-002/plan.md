# BULLGOD-DISCOVERY-002 plan and trust decision

Gate A passed before Gate B began. DISCOVERY-001 merged as
`40958f392bca59009224fcebfd1b636a861615ab`; automatic master run 42550651190
passed all five jobs. Documentation-only integration closeout
`f659349785acf98905901a5cc53921436a109dbc` synchronized master at 0/0 and is the
base of `codex/bullgod-discovery-002`. See the
[integration report](../bullgod-discovery-001/integration.md).

## Scope and source of truth

Connect the existing selection engine to host-controlled, read-only evidence.
Do not create an identity registry, scheduler, approval service, memory engine,
public endpoint or autonomous dispatch path. Do not start a model/runtime merely
to obtain observations. Existing service and private agent contents stay intact.

Native identities come from the existing strict registry. Current turn policy and
authority require the already attached delegation tool; an offline registry view
cannot supply a current caller context. No existing authenticated native-isolated
capability proof provider was found. Missing native proof remains missing.

External bindings come from existing initialized private operator records and
credential/launch material explicitly selected by the trusted host. This list is
not a second identity registry. Preserve actual runtime IDs; the retained Codex
runtime is `acceptance-runtime`, not an invented `codex` alias. Operator ownership,
ancestor/schema checks and audit/state consistency authenticate local-account
provenance under the existing same-UID/root trust boundary. A content digest or
review packet alone is not provenance. HMAC runtime observations are a separate
current-state check, tied to the real action and request nonce.

Existing adapter `discover` can start a process or write request bookkeeping.
Add a narrow authenticated `inspect` action on an already running adapter. It
must not invoke existing discover, prepare, preflight, a model, native process,
task, conversation or publication. Inspection must preserve the signed action;
the host must not fabricate a fresh discover envelope from cached data.

## Components and ownership

1. Sol 6.1/high production worker owns `agent/discovery/runtime_readers.py`,
   necessary discovery integration, narrow `agent/external/` read-only hooks and
   `tests/test_discovery_runtime_readers.py`. Stronger reasoning is required for
   cross-component provenance, current authority, SQLite and accidental dispatch.
2. Luna/high acceptance worker owns only
   `tests/test_discovery_runtime_acceptance.py`. Use real temporary operator
   records and authenticated runtime inspection; synthetic callbacks alone do
   not prove the trusted reader integration.
3. Lead owns actual read-only runtime acceptance, documentation, integration,
   validation and Git. One separate high-reasoning review follows implementation.

The host API is `TrustedDiscoveryHost`: explicit `observe_external(...,
contact_authorized=True)` gathers observations; `select` and `revalidate` never
contact runtimes. `ExistingRuntimeBinding.from_private_files` loads existing
private credentials, frozen task and operator state without creating schema or
writing authority. Native attached-context and initialized recovery observations
are supported where those real objects exist; absent context/admission remains
unknown. All results retain `dispatch_permitted=false`.

## Evidence rules

- Validate owner-controlled probe bytes against the approved probe digest,
  current operator decision/audit, identity/mechanism, exact contract, source,
  config, model/provider and profile bindings.
- Require fresh authenticated inspection for current runtime state. Process or
  socket existence and historical success do not prove admission.
- Distinguish enabled, enrolled, authorized, exact-task approved, healthy,
  available, at capacity, revoked, expired, unavailable and unknown.
- Read-only connection paths must not create tables or task/approval/intent rows.
  Record any SQLite connection bookkeeping separately from execution effects.
- Do not export raw credentials, paths, instructions, transcripts or memory.
  Host binding paths and proof inputs are never part of model-facing requirements.

Initial actual inventory found all three retained external enrollment scopes
expired. Named-agent approved source fingerprints differ from current source.
Sockets remain on disk, which establishes no availability. No approvals or
credentials will be refreshed to make this acceptance pass. Actual missing proof
or admission will remain an explicit limitation and can require a PARTIAL result.

## Acceptance and publication

Implement focused proof/admission, authenticity, drift/revocation, identity/task
binding, unavailable/capacity, revalidation and no-dispatch tests. Use the existing
isolated `scripts/ci_test.py`; no paid models or live authority changes.

Conduct the ten specified live/read-only scenarios against the original service
and real identities, with disposable fixtures for controlled adverse changes.
Capture before/after operator intent counts, service and configuration/profile
metadata, and instrumentation proving zero submissions, native/model execution,
publication and conversation turns. Private memory content is excluded.

Run existing adapter/operator/recovery compatibility tests and the full hosted
macOS/Python 3.13, Linux/Python 3.11/3.13, JavaScript, TypeScript/build and Ruff
gate. Resolve the one independent review's actionable findings. Publish sanitized
receipts and the README, then a draft PR at upstream 0/0. Do not merge 002.
