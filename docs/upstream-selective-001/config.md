# Configuration write-lock port

## Source and defect

The source is upstream commit `4b3ea15ccf249c9017f15a2bb023884d81f845f6` (upstream PR #3911). It fixes a lost-update race in `ModelsHandler.POST`. Each console save reads and then rewrites all of `config.json`. The models actions did not use the shared settings lock, while settings and channel saves did. A models save could therefore write an old snapshot after another save had succeeded. The file remained valid JSON and no error reported the lost update.

A deterministic baseline reproduction held the models snapshot after its read, completed a settings update, then released the models save. The settings response succeeded and `config.conf()` showed `enable_thinking=True`, but `config.json` ended with `enable_thinking=False`. This confirms a silent persisted-state loss.

## Change

`ModelsHandler.POST` now sends every config-writing action through `_config_write_guard()`. The action dispatch moved to `_dispatch_write_action()` without changing its individual handlers. `discover_models` stays outside the lock because it makes a provider network request and does not write config. A slow request must not block unrelated settings saves. Catalog writes remain on the guarded path.

The focused regression checks lock ownership for model write actions and concurrent persistence of provider credentials with general settings, model selection, nested settings, reasoning maps, and a channel credential. It also checks a normal single save and confirms discovery does not hold the lock. Credentials in tests are dummy values only.

## Verification

Command:

```sh
TIKTOKEN_CACHE_DIR=/private/tmp/cow-infra-tiktoken-cache \
  /Volumes/Predator\ SSD\ GM7\ 1TB/Projects/CowAgent/.venv/bin/python \
  scripts/ci_test.py tests/test_models_config_write_lock.py -q
```

Result: 13 passed. No provider network call or live service was used.
