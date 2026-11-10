# Shared SSRF guard port

## Source

This port applies upstream commits `cfbc31ff283d783026c79550cf5fdc06bae7694b` (PR #3913) and `5ae2c2b7ef8d3d1cb97c5eef6487e4ca7ccf60df` (PR #3916), in that order.

The first commit adds `not ip.is_global` to `agent.tools.utils.url_safety._is_blocked_ip()`. The prior checks did not reject the RFC 6598 shared address range, including `100.100.100.200`.

The second commit removes Feishu's duplicate IP classifier. Feishu image validation now calls `validate_url_safe()` inside `strict_url_guard()`. The strict context keeps model-supplied Markdown image URLs guarded when the global SSRF option is off. Redirects continue to pass through validation before each request.

## Scope and policy

The global shared guard remains opt-in. The strict context applies only during Feishu image validation, so approved HTTP readers keep their existing policy and the explicit local-development localhost opt-in stays available. No approved-reader or fixed-destination transport code changed. No compatibility adjustment to either upstream regression test was needed; the Feishu test file now matches upstream commit `5ae2c2b7` byte for byte.

## Verification

Command:

```sh
TIKTOKEN_CACHE_DIR=/private/tmp/cow-infra-tiktoken-cache \
  /Volumes/Predator\ SSD\ GM7\ 1TB/Projects/CowAgent/.venv/bin/python \
  scripts/ci_test.py \
  tests/test_url_safety_shared_address_space.py \
  tests/test_feishu_shared_address_ssrf.py \
  tests/test_feishu_markdown_images.py \
  tests/test_url_safety_allowlist.py
```

Result: 47 passed in 0.27 seconds. The tests cover shared-address literals and DNS results, redirect targets, no-GET behavior, global-off Feishu protection, public controls, prior blocks, allowlist behavior, and normal Markdown image handling. The upstream Feishu regression file was restored unchanged (19 cases); the shared URL guard regression file was also ported unchanged (8 cases).

## Limits

No live service, credential, provider, or external network request was used. The guarded test runner blocks connections outside owned local fixtures.
