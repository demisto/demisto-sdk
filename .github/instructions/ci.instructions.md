---
applyTo: ".github/workflows/**/*.yml,.github/actions/**/*.yml,.gitlab/**/*.yml,.gitlab-ci.yml,.pre-commit-config.yaml,.pre-commit-hooks.yaml"
---

# Copilot instructions — CI / pre-commit configuration

Read together with the repo-wide
[`copilot-instructions.md`](../copilot-instructions.md).

This file applies to GitHub Actions workflows, composite actions, GitLab
CI pipelines, and the pre-commit configurations.

## Repos and pipelines

- **GitHub Actions** ([`.github/workflows/`](../workflows))
  - [`on-push.yml`](../workflows/on-push.yml) — main CI on push / PR.
  - [`handle_new_contribution.yml`](../workflows/handle_new_contribution.yml)
    — community PR triage.
  - [`release-to-pypi.yml`](../workflows/release-to-pypi.yml) — publishes
    `demisto-sdk` to PyPI.
  - [`sdk-release.yml`](../workflows/sdk-release.yml) — release flow.
- **Composite actions** ([`.github/actions/`](../actions))
  - [`setup_environment`](../actions/setup_environment) — installs Poetry,
    Python, deps.
  - [`setup_test_environment`](../actions/setup_test_environment) — extra
    setup for tests (Neo4j, Docker, etc.).
  - [`validate`](../actions/validate) — runs `pre-commit` and `validate`.
  - [`test_summary`](../actions/test_summary),
    [`upload_artifacts`](../actions/upload_artifacts) — reporting.
- **GitLab CI** ([`.gitlab-ci.yml`](../../.gitlab-ci.yml),
  [`.gitlab/`](../../.gitlab)) — internal mirror pipeline.

## Conventions

- **Reuse the composite actions.** New jobs that need a Python + Poetry
  environment must call
  [`./.github/actions/setup_environment`](../actions/setup_environment),
  not re-implement Poetry installation inline.
- **Pin third-party actions** by full SHA or by a major-version tag where
  the action is trusted (`actions/checkout@v4`, `actions/setup-python@v5`,
  `astral-sh/setup-uv@v3`). Avoid `@master` / `@main`.
- **Matrix Python versions** must include 3.9, 3.10, 3.11 (and 3.12 where
  applicable) to match the supported set in
  [`pyproject.toml`](../../pyproject.toml).
- **Caching:** the setup action handles Poetry's virtualenv and pip
  caches. Don't re-cache the same paths from a job.
- **Concurrency:** workflows use `concurrency.group` to cancel in-flight
  duplicates. Preserve this pattern when adding new triggered workflows.
- **Secrets** come from repo settings. Never embed credentials in YAML;
  reference `${{ secrets.NAME }}`. Mirror to GitLab via vault, not
  hard-coded `variables:`.
- **Artifacts:** prefer the
  [`upload_artifacts`](../actions/upload_artifacts) composite action so
  retention and naming stay consistent.

## Pre-commit

- [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml) governs hooks
  that run on **this repo's** commits (ruff, ruff-format, toml-sort,
  validate-pyproject, poetry-check, mypy, plus local hygiene hooks).
- [`.pre-commit-hooks.yaml`](../../.pre-commit-hooks.yaml) declares the
  hooks **this repo exposes** to other repos (consumed by `content`).
  Changing IDs, entries, or `language` here is a public-API change and
  needs a `breaking` changelog entry.

When updating hook revisions:

1. Update the `rev:` to the latest tested version.
2. Run `poetry run pre-commit run --all-files` locally and fix any new
   findings.
3. Add a `internal` (or `fix`/`feature`, as appropriate) changelog entry
   via `poetry run sdk-changelog --init -n <PR>`.

## Hard rules

- **No `latest` tags** for actions, container images, or pip installs in
  CI YAML. Pin everything.
- **No interactive `pip install`s of unpinned versions** outside the
  Poetry-managed env. The build must be reproducible.
- **No skipping `pre-commit` in CI** with `SKIP=...` for new hooks.
- **Don't disable a job** just because it's flaky — fix the underlying
  flakiness. If a job is genuinely deprecated, remove it and document
  why in the PR description.
- **Don't introduce a third CI system.** GitHub Actions is the canonical
  pipeline; GitLab is a mirror. New automation goes into GitHub Actions
  first.
