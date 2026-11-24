---
applyTo: "demisto_sdk/commands/lint/**/*.py,demisto_sdk/commands/xsoar_linter/**/*.py"
---

# Copilot instructions — content linters (`lint`, `xsoar_linter`)

Read together with the repo-wide
[`copilot-instructions.md`](../copilot-instructions.md) and
[`commands.instructions.md`](commands.instructions.md). This file specialises
guidance for the linters the SDK ships **for content code** (not for the
SDK's own source).

> Important: the SDK's own Python is linted by **ruff** + **mypy** (see
> [`pyproject.toml`](../../pyproject.toml)). The commands documented here
> lint *content* — i.e. integration / script Python and PowerShell code
> shipped by content packs.

## Scope

| Path | What it lints / what it is |
|---|---|
| [`demisto_sdk/commands/lint/`](../../demisto_sdk/commands/lint) | Legacy `demisto-sdk lint` orchestrator (largely superseded by [`pre_commit`](../../demisto_sdk/commands/pre_commit) but still consumed). Runs flake8 / pylint / mypy / bandit / pytest inside per-image Docker containers. |
| [`demisto_sdk/commands/xsoar_linter/`](../../demisto_sdk/commands/xsoar_linter) | XSOAR-specific linter (`demisto-sdk xsoar-lint`). Parses integration / script Python with the standard library `ast` module and reports `E`/`W` codes. Does not use pylint. |
| [`demisto_sdk/commands/xsoar_linter/checkers/`](../../demisto_sdk/commands/xsoar_linter/checkers) | The rules, one checker class per support level (`base_checker`, `partner_checker`, `certified_partner_checker`, `xsoar_checker`), plus the shared runner, disable-comment (`pragmas`) and name-resolution code. |

Authoritative orchestrator: [`xsoar_linter.py`](../../demisto_sdk/commands/xsoar_linter/xsoar_linter.py)
runs the checkers per file in a process pool. Which checkers run for each support level
(`base` ⊂ `community` ⊂ `partner` ⊂ `certified partner` ⊂ `xsoar`) is defined in
[`checkers/registry.py`](../../demisto_sdk/commands/xsoar_linter/checkers/registry.py).

## Hard rules

1. **Do not add new linting features to
   [`commands/lint/`](../../demisto_sdk/commands/lint).** It is in
   maintenance mode. New checks belong in
   [`pre_commit`](../../demisto_sdk/commands/pre_commit) and
   [`xsoar_linter`](../../demisto_sdk/commands/xsoar_linter).
2. **All container interactions go through
   [`commands/common/docker/`](../../demisto_sdk/commands/common/docker)
   and [`docker_helper.py`](../../demisto_sdk/commands/common/docker_helper.py).**
   Don't `import docker` directly in lint code; use the existing wrappers
   so retry/auth/registry behaviour stays consistent.
3. **Honour the support-level hierarchy.** A check that applies to
   `base` automatically applies to `community`/`partner`/`certified
   partner`/`xsoar`. Don't duplicate a check across levels — put it at
   the lowest applicable level and let the level loader pick it up.
4. **Honour `DEMISTO_SDK_OFFLINE_ENV`** and `--no-docker`. Linters that
   require a Docker image must skip cleanly with a clear log message
   when Docker is unavailable.
5. **Errors are codes, not free text.** xsoar-linter rules must use
   stable `E####` / `W####` IDs and symbols so content authors can
   suppress them precisely (`# xsoar-lint: disable=<code or symbol>`).
   Do not change an existing code's meaning.
6. **Never import pylint or astroid in xsoar-linter.** They are not SDK
   dependencies. The checkers only parse the file with `ast`; they never
   import or execute content code.

## Adding an xsoar-linter rule

1. Decide which support level it belongs to (`base` is the floor: every
   integration runs it). Pick the matching checker under
   [`commands/xsoar_linter/checkers/`](../../demisto_sdk/commands/xsoar_linter/checkers).
2. Add a `Rule(code, symbol, message)` to the checker's `RULES` list,
   with a new code (`E####` for errors, `W####` for warnings).
3. Implement the check in a `visit_<NodeType>` method (or `leave_module`
   for whole-file rules) and call `self.report(code, node)`.
4. Add tests next to the existing ones in
   [`commands/xsoar_linter/tests/`](../../demisto_sdk/commands/xsoar_linter/tests):
   a positive and a negative source snippet. For golden cases, add a
   sample under `tests/test_files/golden/samples/` and write the expected
   result in `golden.json` by hand.
5. Document the new code in the relevant content-author docs (xsoar.pan.dev
   linked from [`xsoar_linter/README.md`](../../demisto_sdk/commands/xsoar_linter/README.md)).
6. Add a `feature` (or `fix`) changelog entry.

## Adding a Docker-based check (`lint` orchestrator)

If you really must extend [`commands/lint/`](../../demisto_sdk/commands/lint)
for a bug fix:

1. Use the existing per-image Docker runner. Do not spawn raw containers.
2. Cap timeouts. Linters running inside images must terminate; never
   wait indefinitely.
3. Stream stdout/stderr through the project `logger`. Do not buffer to
   a temp file unless the consumer downstream needs the file.
4. Surface non-zero exit codes from inside the container as a clear,
   parseable error in the parent process, with the image name and the
   inner command captured.

## Don'ts

- **Don't pin a specific Docker image tag** in lint code. Image
  selection is driven by the integration's `script.dockerimage` and the
  native-image config in
  [`commands/common/native_image.py`](../../demisto_sdk/commands/common/native_image.py)
  / [`docker_images_metadata.py`](../../demisto_sdk/commands/common/docker_images_metadata.py).
- **Don't introduce parallelism primitives** (`multiprocessing`,
  `concurrent.futures`) without coordinating with the existing
  per-CPU bounds in
  [`xsoar_linter.py`](../../demisto_sdk/commands/xsoar_linter/xsoar_linter.py)
  and [`commands/common/cpu_count.py`](../../demisto_sdk/commands/common/cpu_count.py).
- **Don't broaden the "skip" list** silently. If a path or pattern is
  excluded, it must be documented in the README and in a changelog
  entry.
- **Don't change the regex used to parse the linter output**
  ([`ERROR_AND_WARNING_CODE_PATTERN`](../../demisto_sdk/commands/xsoar_linter/xsoar_linter.py))
  without updating downstream consumers (CI report parsers, the content
  build).
- **Don't embed colour or rich formatting** in lint messages. Output
  is consumed by CI log scrapers and IDE problem matchers; plain text
  with stable codes is the contract.

## Tests

- Use the small fixture content under
  [`commands/xsoar_linter/tests/test_files/`](../../demisto_sdk/commands/xsoar_linter/tests/test_files).
- Mock Docker — never pull an image in a unit test. The
  [`tests.instructions.md`](tests.instructions.md) ban applies here.
- A check is considered tested when (a) a positive sample triggers the
  expected code exactly once and (b) a negative sample triggers nothing
  from this checker.
