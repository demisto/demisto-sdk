---
applyTo: "tests_end_to_end/**/*.py"
---

# Copilot instructions — end-to-end tests

Read together with the repo-wide
[`copilot-instructions.md`](../copilot-instructions.md) and
[`tests.instructions.md`](tests.instructions.md).

[`tests_end_to_end/`](../../tests_end_to_end) contains **live** tests that
run real `demisto-sdk` flows against real Cortex XSOAR / XSIAM /
XSOAR-SaaS tenants. They are excluded from the wheel and are not part of
the default `pytest` run.

## Layout

```
tests_end_to_end/
├── e2e_tests_constansts.py     # Shared constants (note the historical typo; do not rename)
├── e2e_tests_utils.py          # Shared helpers (env vars, login, tenant URL, etc.)
├── general/
│   └── test_dockerserver.py
├── xsoar/
│   └── test_e2e_demisto_sdk_flow_playbook_xsoar.py
├── xsiam/
│   └── test_e2e_demisto_sdk_flow_playbook_xsiam.py
└── xsoar-saas/
    └── test_e2e_demisto_sdk_flow_playbook_xsoar_saas.py
```

## Conventions

- E2E test files are named **`test_*.py`** (the historic convention here),
  not `*_test.py`. Don't rename existing ones; match the directory's
  pattern when adding new ones.
- One test file per flow per platform (XSOAR / XSIAM / XSOAR SaaS). Don't
  cross-reference flows between platforms.
- Get tenant URL / API key / `XSIAM_AUTH_ID` from environment variables
  via [`e2e_tests_utils.py`](../../tests_end_to_end/e2e_tests_utils.py).
  Skip the test (`pytest.skip`) cleanly when env is missing — don't fail.
- Teardown is mandatory. Anything created on a tenant (incidents, packs,
  jobs) must be deleted in a `try/finally` or pytest fixture
  `addfinalizer` to keep tenants clean.

## Hard rules

- **Never hard-code credentials.** All secrets come from env vars / CI
  vault.
- **Never run against a customer tenant.** Only the dedicated CI tenants
  configured in
  [`.gitlab-ci.yml`](../../.gitlab-ci.yml) /
  [`.github/workflows/`](../workflows).
- **No assertions on production-only data** (existing packs, incidents,
  users). Every assertion must be on something the test itself created.
- **Mark slow tests** so the default suite stays fast.
  `@pytest.mark.e2e` is appropriate; check the closest existing tests for
  the marker style in use.
- **No unit-test-style mocking.** If a test needs to mock something, it
  belongs under `demisto_sdk/.../tests/`, not here.

## Don'ts

- Don't import from `TestSuite/` here. E2E tests run against real tenants
  and should construct content on disk via the same `demisto-sdk` CLI
  paths a real user would (`demisto-sdk init`, `demisto-sdk upload`, …).
- Don't introduce new top-level dependencies just for E2E (use the
  existing dev stack).
