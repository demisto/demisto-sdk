---
applyTo: "**/tests/**/*.py,**/*_test.py,conftest.py"
---

# Copilot instructions — tests

These rules apply to **every test file** in the repo (anything under a
`tests/` directory or named `*_test.py`, plus `conftest.py`). Read them in
addition to the repo-wide [`copilot-instructions.md`](../copilot-instructions.md).

## Naming and layout

- Test files **must end in `_test.py`** (e.g. `validate_manager_test.py`).
  The `name-tests-test` pre-commit hook (see
  [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml)) blocks
  `test_*.py` in production sub-trees. Do not generate `test_foo.py`.
- Tests live next to the code they cover, in a `tests/` subdirectory:
  `demisto_sdk/commands/<cmd>/tests/<thing>_test.py`.
- Test classes are optional. Free-standing `def test_<behaviour>():`
  functions are preferred unless grouping shared fixtures.
- Test functions should be named `test_<unit>_<scenario>_<expectation>`,
  e.g. `test_validate_returns_error_when_rolename_set`.

## Frameworks and fixtures

- Use **pytest** + **`pytest-mock`** (`mocker` fixture).
- Mock HTTP with **`requests-mock`** (`requests_mock` fixture).
- Mock subprocess with **`pytest-subprocess`** (`fp` fixture).
- Freeze time with **`pytest-freezegun`** (`@pytest.mark.freeze_time(...)`)
  rather than monkey-patching `datetime`.
- Use the **`tmp_path`** / **`tmp_path_factory`** fixtures for any
  filesystem work. Never write to `~`, `/tmp` directly, the repo root, or
  `CONTENT_PATH`.
- For loguru output assertions, use **`pytest-loguru`** (`caplog`-style).
- For data files, prefer **`pytest-datadir-ng`** over hard-coded paths.

## Building content fixtures

Do **not** hand-craft YAML / JSON in tests when a builder exists. Use the
in-repo [`TestSuite/`](../../TestSuite) builders:

```python
from TestSuite.repo import Repo

def test_something(tmp_path):
    repo = Repo(tmp_path)
    pack = repo.create_pack("MyPack")
    integration = pack.create_integration("MyIntegration")
    integration.create_default_integration()
    playbook = pack.create_playbook("MyPlaybook")
    playbook.create_default_playbook()
    # ... assert against integration.path / playbook.yml etc.
```

Available builders (one class per file):
[`Pack`](../../TestSuite/pack.py), [`Integration`](../../TestSuite/integration.py),
[`Playbook`](../../TestSuite/playbook.py), [`Repo`](../../TestSuite/repo.py),
[`Classifier`](../../TestSuite/classifier.py),
[`Mapper`](../../TestSuite/mapper.py),
[`Layout`](../../TestSuite/layout.py),
[`IncidentField`](../../TestSuite/incident_field.py),
[`IndicatorField`](../../TestSuite/indicator_field.py),
[`ModelingRule`](../../TestSuite/modeling_rule.py),
[`ParsingRule`](../../TestSuite/parsing_rule.py),
[`CorrelationRule`](../../TestSuite/correlation_rule.py),
[`Dashboard`](../../TestSuite/dashboard.py),
[`Job`](../../TestSuite/job.py), [`AgentixAgent`](../../TestSuite/agentix_agent.py),
[`AgentixAction`](../../TestSuite/agentix_action.py), and others.

## Hard rules

1. **No real network calls.** Always mock `requests`, `demisto_client`,
   `pygithub`, `python-gitlab`, Neo4j, Docker, and Slack SDK clients.
2. **No real Docker calls.** Mock `docker.from_env()` /
   `DockerBase.client`. The CI runners block image pulls in unit tests.
3. **No reliance on the user's git identity, real `~/.netrc`, real
   `~/.demisto-sdk/`, or env-var leakage.** Set / unset env vars via
   `monkeypatch.setenv` / `monkeypatch.delenv`.
4. **Determinism.** Avoid `time.sleep`, real timestamps, real UUIDs.
   Patch `uuid.uuid4`, `datetime.now`, `time.time` if needed.
5. **Speed.** Aim for < 1 s per test. Tests that need a live Neo4j /
   XSOAR server belong in [`tests_end_to_end/`](../../tests_end_to_end),
   not under `demisto_sdk/`.
6. **Coverage.** Each new function / branch must have at least one happy-path
   test and one failure-path test (invalid input, missing file, error
   propagation).
7. **Assertions.** Use plain `assert` statements (pytest rewrites them).
   Don't use `unittest.TestCase` for new tests.
8. **Logger imports stay banned even in tests.** Use the project
   `logger` from `demisto_sdk.commands.common.logger` if you need to log;
   otherwise use the `caplog` fixture to assert on log output.

## What you may relax in tests

- `print()` / `pprint()` are still banned (ruff `T20` applies).
- Type annotations are encouraged but not required on test functions
  (mypy excludes `tests/.*`, see [`pyproject.toml`](../../pyproject.toml)).
- You may import `json` / `yaml` only if you are constructing intentionally
  invalid input that the project handlers would refuse to round-trip — and
  even then, prefer the project handlers and use raw strings via
  `path.write_text(...)`.

## Example skeleton

```python
from __future__ import annotations

import pytest

from demisto_sdk.commands.common.logger import logger
from TestSuite.repo import Repo


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path)


def test_my_validator_flags_bad_playbook(repo, mocker):
    pack = repo.create_pack("Sample")
    playbook = pack.create_playbook("Bad")
    playbook.yml.update({"rolename": ["analyst"]})

    mocker.patch(
        "demisto_sdk.commands.some_module.external_call",
        return_value="ok",
    )

    from demisto_sdk.commands.validate.validators.PB_validators.PB100_is_no_rolename import (
        IsNoRolenameValidator,
    )

    results = IsNoRolenameValidator().obtain_invalid_content_items([playbook.object])

    assert len(results) == 1
    assert "rolename" in results[0].message
```
