# Reproduce the EFFICIENCY-001 baseline

Run from the repository root with the existing project `.venv`. The captured
baseline uses Python 3.13.1 and SQLite 3.45.3. Application dependencies come from
the project's normal setup; optional audit dependencies are pinned separately:

```sh
.venv/bin/python -m pip install -r scripts/requirements-efficiency-audit.txt
```

The benchmark is specific to the retained TestPilot two-call case whose stored
usage is 20,208 input / 160 output tokens. It fails if that case is absent. Future
prompts, source revisions, model routes and provider availability can change
counts. The saved JSON is the immutable historical evidence, not a promise that
later calls will produce the same numbers.

## Create a private snapshot

The snapshot contains private runtime data. Keep it outside the repository and
backup/sync roots, with private directory permissions. Never commit it. Use
SQLite's backup API from read-only sources; do not copy a live main database
without its committed WAL state, checkpoint the source, or remove sidecars.

Set the existing configuration path. The following script creates a new private
directory and prints only its location and a database count. It does not change
the config or open the source databases for SQL writes. A read-only SQLite source
may use its existing WAL/shared-memory coordination files. A main-file hash change
is recorded as concurrent activity, not proof of an audit write; each backup is
transactionally consistent, but the entire workspace is not a cross-file atomic
snapshot if another process is editing it.

```sh
export EFFICIENCY_CONFIG='/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData/config.json'
.venv/bin/python - <<'PY'
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

cfg = json.loads(Path(os.environ['EFFICIENCY_CONFIG']).read_text())
source = Path(cfg['agent_workspace']).resolve()
if any(p.is_symlink() for p in source.rglob('*')):
    raise SystemExit('Source contains symlinks; prepare a reviewed snapshot instead')
root = Path(tempfile.mkdtemp(prefix='cowagent-efficiency-001-'))
root.chmod(0o700)
snapshot = root / 'workspace'
snapshot.mkdir()
databases = []
for path in source.rglob('*'):
    target = snapshot / path.relative_to(source)
    if path.is_dir():
        target.mkdir(exist_ok=True, parents=True)
    elif path.is_file() and path.suffix == '.db' and '[conflicted' not in path.name:
        databases.append((path, target))
    elif path.is_file() and '.db' not in path.name:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
receipts = []
for path, target in databases:
    target.parent.mkdir(parents=True, exist_ok=True)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    src = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    dst = sqlite3.connect(target)
    try:
        src.execute('PRAGMA query_only=ON')
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    receipts.append({
        'database_sha256_before': before,
        'main_unchanged_during_backup': before == hashlib.sha256(path.read_bytes()).hexdigest(),
    })
(root / 'snapshot-receipt.json').write_text(json.dumps(receipts, indent=2) + '\n')
print(json.dumps({'snapshot_parent': str(root), 'databases_backed_up': len(databases)}))
PY
```

Set `EFFICIENCY_ROOT` to the printed `snapshot_parent`, then run the offline
baseline. Keep the original configuration file as the credential source; the
runner rewrites workspace paths only in its in-memory configuration.

```sh
export EFFICIENCY_ROOT='/private/tmp/cowagent-efficiency-001-REPLACE_WITH_CREATED_DIRECTORY'
.venv/bin/python scripts/benchmark_context_cache.py \
  --config "$EFFICIENCY_CONFIG" \
  --snapshot "$EFFICIENCY_ROOT/workspace" \
  --output "$EFFICIENCY_ROOT/offline.json" \
  --revision 37d947bb
```

Use the actual source revision when reproducing a different checkout. The runner
rejects overlapping active/snapshot roots, snapshot symlinks and MCP subprocess
configuration. It suppresses application logs, uses only snapshot databases and
emits counts/hashes instead of content. It does not run the full initializer's
credential migration, scheduler, server or history-flush lifecycle. Snapshot
maintenance can write the cloned indexes.

## Optional public model-family tokenizer and template

Download only the two pinned data/text files. No model weights or remote Python
code are needed. The public BF16 variant is from the same named model family;
the exact OpenRouter deployment revision is not confirmed.

```sh
mkdir -p "$EFFICIENCY_ROOT/tokenizer/nemotron"
curl --fail --location \
  'https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/resolve/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/tokenizer.json' \
  --output "$EFFICIENCY_ROOT/tokenizer/nemotron/tokenizer.json"
curl --fail --location \
  'https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/resolve/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/chat_template.jinja' \
  --output "$EFFICIENCY_ROOT/tokenizer/nemotron/chat_template.jinja"
shasum -a 256 "$EFFICIENCY_ROOT/tokenizer/nemotron/tokenizer.json" \
  "$EFFICIENCY_ROOT/tokenizer/nemotron/chat_template.jinja"
```

Expected SHA-256:

- tokenizer: `d0432ad8b1c2984a2e2dca82e1933e3fd5628df6e95c51fba4c3ee9950dce299`
- template: `1369e90b19976f99ce2070eb21ade8fcb4af640f008e14e82af5c5e89a9cc816`

Run the same offline command with these additional options:

```sh
  --tokenizer-json "$EFFICIENCY_ROOT/tokenizer/nemotron/tokenizer.json" \
  --chat-template "$EFFICIENCY_ROOT/tokenizer/nemotron/chat_template.jinja" \
  --tokenizer-label 'NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16@fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe'
```

The renderer uses sandboxed Jinja and `tokenizers`, with no remote code execution.
Function-block attribution is specific to this template's structure. It fails
when block counts do not match; it must not silently report a partial breakdown.
Raw JSON, standalone text and full-template estimates have separate fields.

## Opt-in live comparison

Add `--live` and the model selection below to the benchmark command. This sends
the reconstructed private request through the already configured OpenRouter
endpoint using its existing credential. It saves numeric usage and hashes, not
prompt/response bodies. It does not replace model selection in production.

```sh
  --live \
  --models nvidia/nemotron-3.5-super-vl:free \
    google/gemma-4-26b-a4b-it:free openrouter/free
```

For each model the sequence is first request, optional one-step indexed-memory
continuation, identical first-request repeat, then a separate title request.
Other tools remain in the schema but cannot execute in this harness. No automatic
retry is used. HTTP error bodies are omitted because they can echo private input.
Do not infer a cold cache or causal speedup from the sequence. Keep errors and
missing usage in the result instead of filling them with zero. Use `--models`
with only Gemma for a later availability follow-up; honor any provider retry hint.

The committed `baseline.json` combines the main campaign's 11 receipts, the
three-request Gemma follow-up and later offline native-template measurements.
The first-request hash stayed identical across these offline refinements. Exact
UTC timestamps were absent in the first campaign. Follow-up timestamps mark
response-header receipt; the current runner captures request start. The request
durations and sequence are retained without inventing missing timestamps.

## Focused regression checks

```sh
COW_DATA_DIR="$EFFICIENCY_ROOT/audit-logs" .venv/bin/python -m pytest -q \
  tests/test_efficiency_metrics.py \
  tests/test_efficiency_adapter_baseline.py \
  tests/test_efficiency_accounting_baseline.py \
  tests/test_efficiency_benchmark.py
.venv/bin/python -m ruff check --select F \
  scripts/benchmark_context_cache.py scripts/efficiency_metrics.py \
  tests/test_efficiency_metrics.py tests/test_efficiency_adapter_baseline.py \
  tests/test_efficiency_accounting_baseline.py tests/test_efficiency_benchmark.py
git diff --check
```

These synthetic tests check counts/hashes and privacy, exact prompt-section
reassembly, template attribution, current adapter forwarding/cache normalization,
latest-call versus run accounting, stale cached-prompt chart behavior, separate
title requests and snapshot boundaries. They make no provider calls and do not
open production databases. They characterize current accounting defects; future
fixes must update the expected contract deliberately. The implementation plan
defines the additional before/after task and cache checks required for optimization.
