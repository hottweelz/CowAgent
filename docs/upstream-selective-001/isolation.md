# Cloud identity isolation

Accepted baseline `74b75f97e933d36e7b1b0a80b8d20afe16cbf8b2` contains both
failure fallbacks. Its memory/knowledge/workspace constructors return the default
service on exception, and `_agent_workspace` returns `None` on registry failure.
Neither was independently corrected by PERSONAL-001–004.

- Candidate 1: [f15ba96be2d38ebb9ae0ac02aebe3bac4fd43b79](https://github.com/zhayujie/CowAgent/commit/f15ba96be2d38ebb9ae0ac02aebe3bac4fd43b79), [PR 3914](https://github.com/zhayujie/CowAgent/pull/3914).
- Candidate 2: [168178bf3eb2c4933d40d0094c4b9f4d5ecde89f](https://github.com/zhayujie/CowAgent/commit/168178bf3eb2c4933d40d0094c4b9f4d5ecde89f), [PR 3921](https://github.com/zhayujie/CowAgent/pull/3921).

Both original PR descriptions and maintainer responses were read. Both are
merged upstream. Selective ports preserve the fork's blocked legacy peer route;
the second patch's class insertion needed local context adjustment because the
fork does not contain upstream's new guest-page constants. No guest feature was
imported. The two upstream test files are unchanged.

Named construction or registry failures now return service-unavailable errors
without default dispatch. Unknown IDs retain 404. Only absent IDs select the
existing process-default service. History resolution fails before opening a
store when the registry is unavailable.

Verification (existing Python 3.13 virtual environment; prepared cache):

```sh
TIKTOKEN_CACHE_DIR=/private/tmp/cow-infra-tiktoken-cache '/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python' scripts/ci_test.py -q tests/test_cloud_agent_service_build_failure.py tests/test_cloud_agent_registry_unavailable.py tests/test_cloud_agent_scoping.py
# 43 passed in 0.54s
TIKTOKEN_CACHE_DIR=/private/tmp/cow-infra-tiktoken-cache '/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python' scripts/ci_test.py -q tests/test_cloud_three_agent_isolation.py
# 33 passed in 0.24s
```

The second suite uses real callbacks and a disposable three-profile registry for
`default`, `testpilot`, `testpilot2`. File-backed service doubles prove healthy
read/write ownership, zero dispatch on build/registry failure, unchanged other
identity files and correctly routed history. It does not claim live cloud or
production SQLite acceptance. An initial standalone collection lacked optional
LinkAI; the fixture now follows the existing cloud tests' SDK stub pattern.

Conflict risk: low. Production profile, memory, approval and credentials are not
read or changed. Final integrated regression and independent review are recorded
in the main report.
