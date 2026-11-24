# Weak-Copyleft (LGPL / MPL) Dependency Verification

**Ticket:** [CIAC-17461](https://jira-dc.paloaltonetworks.com/browse/CIAC-17461)  (follow-up to CIAC-17285)
**Repository:** `demisto-sdk`
**Repo version at verification time:** `1.39.10` (per `pyproject.toml`)
**Verified on:** 2026-09-27
**Verified by:** Shachar Kidor

## Purpose

Confirm that every weak-copyleft (LGPL / MPL) dependency of `demisto-sdk`
is imported and used only as an **unmodified external library** (dynamic
library use model), and is **not vendored or modified**, so the SDK can
transition to a proprietary distribution model while honoring the LGPL /
MPL obligations.

## Packages in scope

| Package         | Version    | License                          | Declaration in `pyproject.toml`         |
|-----------------|------------|----------------------------------|------------------------------------------|
| `paramiko`      | 3.5.1      | LGPL-2.1                         | Direct: `paramiko = ">=3.4.1,<4.0"`      |
| `PyGithub`      | 2.9.1      | LGPL-3.0                         | Direct: `pygithub = "^2.2.0"`            |
| `python-gitlab` | 8.3.0      | LGPL-3.0-or-later                | Direct: `python-gitlab = "^8.0.0"`       |
| `Pebble`        | 5.2.0      | LGPL-3.0                         | Direct: `Pebble = ">=4.6.3,<6.0.0"`      |
| `chardet`       | 5.2.0      | LGPL-2.1+                        | Direct: `chardet = ">=4,<6"`             |
| `certifi`       | 2024.12.14 | MPL-2.0                          | Transitive (via `requests`, `demisto-py`) |
| `astroid`       | 3.3.11     | LGPL-2.1                         | Transitive (via `pylint`)                |
| `orjson`        | 3.11.9     | MPL-2.0 AND (Apache-2.0 OR MIT)  | Direct: `orjson = "^3.8.3"`              |
| `tqdm`          | 4.67.3     | MPL-2.0 AND MIT                  | Transitive (via `nltk`)                  |

All installed versions match the versions listed in CIAC-17461 exactly.

## Verification steps and evidence

### 1. No vendored / bundled copies

**Method.** Recursive search of the repository (excluding `.venv`, `.git`,
build caches, `node_modules`) for any directory whose name matches one of
the 9 target packages or their common Python module names (`paramiko`,
`github`, `gitlab`, `pebble`, `chardet`, `certifi`, `astroid`, `orjson`,
`tqdm`, plus `PyGithub`, `python-gitlab`, `Pebble` variants).

```bash
for pkg in paramiko PyGithub github python-gitlab gitlab \
           Pebble pebble chardet certifi astroid orjson tqdm; do
  find . -type d -iname "$pkg" \
    -not -path "*/.venv/*"        -not -path "*/.git/*" \
    -not -path "*/__pycache__/*"  -not -path "*/.mypy_cache/*" \
    -not -path "*/.pytest_cache/*" -not -path "*/.ruff_cache/*" \
    -not -path "*/node_modules/*"
done
```

**Result.** Zero matches for every package. No vendored copies exist in
the source tree.

### 2. Sourced from PyPI (no `git+` / path / URL dependencies)

**Method.** Parse `poetry.lock` and confirm each package's
`[package.source]` block is either absent (i.e. resolved from the default
PyPI index) or explicitly points to PyPI. Verify `pyproject.toml`
contains no `{ git = ... }` / `{ path = ... }` / `{ url = ... }`
dependency specs.

**Result.**

| Package         | poetry.lock version | Source              | Optional |
|-----------------|---------------------|---------------------|----------|
| `paramiko`      | 3.5.1               | PyPI (default)      | false    |
| `pygithub`      | 2.9.1               | PyPI (default)      | false    |
| `python-gitlab` | 8.3.0               | PyPI (default)      | false    |
| `pebble`        | 5.2.0               | PyPI (default)      | false    |
| `chardet`       | 5.2.0               | PyPI (default)      | false    |
| `certifi`       | 2024.12.14          | PyPI (default)      | false    |
| `astroid`       | 3.3.11              | PyPI (default)      | false    |
| `orjson`        | 3.11.9              | PyPI (default)      | false    |
| `tqdm`          | 4.67.3              | PyPI (default)      | false    |

`pyproject.toml` contains no `git`, `path`, or `url` dependency
overrides. `poetry.lock` contains no non-PyPI URLs.

### 3. Cryptographic integrity of the fetched artifacts

**Method.** Every locked package has one or more SHA-256 file hashes in
`poetry.lock` (for both the wheel and the sdist). These hashes are the
ones published on PyPI and are re-verified by `poetry` / `pip` at every
install, so any local mutation would cause installation to fail.

| Package         | Locked SHA-256 files |
|-----------------|----------------------|
| `paramiko`      | 2                    |
| `pygithub`      | 2                    |
| `python-gitlab` | 2                    |
| `pebble`        | 2                    |
| `chardet`       | 2                    |
| `certifi`       | 2                    |
| `astroid`       | 2                    |
| `orjson`        | 74 (per-wheel-arch)  |
| `tqdm`          | 2                    |

This proves consumers of `demisto-sdk` will always receive the exact,
unmodified upstream artifacts as published on PyPI.

### 4. Distribution model: standard wheel / sdist, no static bundling

**Method.** Inspect `[build-system]` in `pyproject.toml` and search for
any PyInstaller / Nuitka / shiv / pex / one-file bundling configuration.

```toml
[build-system]
requires = ["poetry-core>=1.0.0,<2.0.0"]
build-backend = "poetry.core.masonry.api"
```

**Result.** The build backend is `poetry-core`, which produces a standard
Python wheel and sdist for the `demisto_sdk` package **only** and
declares the 9 libraries as external runtime dependencies. There are:

- No `.spec` files (PyInstaller).
- No Nuitka / shiv / pex configuration.
- No static-link / one-file bundling anywhere in the repo.

The LGPL / MPL libraries are therefore linked dynamically (via the
Python import system) from separate PyPI-installed packages at runtime,
which is the "use as an unmodified library" model required by both LGPL
and MPL section 3.3.

### 5. Import-only usage (no forks, no derivative works)

**Method.** For each package, list every Python source line in the
first-party `demisto_sdk/` tree that imports it.

| Package         | First-party import sites                                                 | Notes                                     |
|-----------------|---------------------------------------------------------------------------|-------------------------------------------|
| `paramiko`      | none in `demisto_sdk/`                                                    | Transitive only                            |
| `PyGithub`      | `demisto_sdk/scripts/changelog/changelog.py`, `demisto_sdk/commands/common/tools.py` (`from github import Github`) | Standard API client use                   |
| `python-gitlab` | none in `demisto_sdk/`                                                    | Transitive only                            |
| `Pebble`        | `demisto_sdk/commands/validate/old_validate_manager.py`, `find_dependencies.py`, `common/tools.py`, `create_artifacts/content_artifacts_creator.py` | Uses `ProcessPool` / `ProcessFuture` |
| `chardet`       | none in `demisto_sdk/`                                                    | Transitive only                            |
| `certifi`       | none in `demisto_sdk/`                                                    | Transitive (used by `requests`)            |
| `astroid`       | 4 pylint plugin files under `demisto_sdk/commands/pre_commit/resources/pylint_plugins/` | Used as pylint's AST library (via pylint) |
| `orjson`        | `demisto_sdk/commands/common/handlers/json/orjson_handler.py` (single import) | Standard JSON API                         |
| `tqdm`          | `demisto_sdk/scripts/validate_content_path.py`, `commands/content_graph/parsers/repository.py`, `commands/content_graph/objects/repository.py` | Standard progress-bar API                  |

In every case, the code uses the library only through its published
public API. No library source is copy-pasted, forked, subclassed for the
purpose of re-exporting, or otherwise modified.

### 6. NOTICE / third-party attribution file

**Before this ticket.** Repository contained a top-level `LICENSE` file
only. No `NOTICE`, `THIRD_PARTY_LICENSES`, `ATTRIBUTIONS`, or
`licenses/` directory existed.

**After this ticket.** Added [`NOTICE`](../../NOTICE:1) at the repo root
which lists every LGPL / MPL dependency, its homepage, PyPI URL,
license, and includes an explicit modification-and-distribution
statement affirming (a) the libraries are used unmodified, (b) they are
not statically bundled, and (c) full license texts / source code are
available upstream on PyPI. The `NOTICE` file is automatically included
in the built sdist by `poetry-core` and can be included in the wheel by
its file-inclusion rules.

## Findings summary

- **Vendoring:** none. Zero vendored copies of any listed package in the
  repository.
- **Modifications:** none. All libraries are consumed from PyPI at the
  exact upstream SHA-256 published by their authors.
- **Distribution model:** standard PyPI wheel + sdist for the
  `demisto_sdk` package only, with the LGPL / MPL libraries declared as
  external runtime dependencies (dynamic-library use model). No static
  linking or one-file bundling.
- **Usage:** import-only via each library's public API - no forks, no
  derivative works.
- **Attribution:** `NOTICE` file added at the repo root listing every
  LGPL / MPL dependency and stating the modification / distribution
  posture.
- **Compliance posture:** `demisto-sdk`'s use of these libraries is
  consistent with LGPL §6 ("use of the Library") and MPL §3.3
  ("distribution of a Larger Work"). No source-release obligation is
  triggered because we neither modify nor combine these libraries into a
  derivative work; we merely depend on them at install time.

## Optional follow-up

The ticket notes an optional simplification: replace `chardet`
(LGPL-2.1+) with `charset-normalizer` (MIT), which is already present in
`poetry.lock` (transitively). This would remove one LGPL dependency but
requires a code change (`chardet` is currently only a transitive dep, so
this may be a no-op in `demisto-sdk` itself - the dependency comes from
one of its transitive parents). To be evaluated separately.

## Reproducing the verification

```bash
cd path/to/demisto-sdk

# 1. Vendoring
for pkg in paramiko PyGithub github python-gitlab gitlab \
           Pebble pebble chardet certifi astroid orjson tqdm; do
  find . -type d -iname "$pkg" \
    -not -path "*/.venv/*" -not -path "*/.git/*" \
    -not -path "*/__pycache__/*" -not -path "*/.mypy_cache/*" \
    -not -path "*/.pytest_cache/*" -not -path "*/.ruff_cache/*"
done  # expect: empty

# 2. Source & version (poetry.lock)
python3 -c "
import re, pathlib
lock = pathlib.Path('poetry.lock').read_text()
targets = {'paramiko','pygithub','python-gitlab','pebble','chardet',
           'certifi','astroid','orjson','tqdm'}
for b in re.split(r'\n(?=\[\[package\]\])', lock):
    m = re.search(r'^name\s*=\s*\"([^\"]+)\"', b, re.M)
    if not m or m.group(1).lower() not in targets: continue
    name = m.group(1).lower()
    ver  = re.search(r'^version\s*=\s*\"([^\"]+)\"', b, re.M).group(1)
    src  = re.search(r'^\[package\.source\]', b, re.M)
    print(f'{name:15s} {ver:12s} source={\"custom\" if src else \"PyPI\"}')
"

# 3. Build backend
sed -n '/^\[build-system\]/,/^\[/p' pyproject.toml

# 4. Import sites
for pkg in paramiko github gitlab pebble chardet certifi astroid orjson tqdm; do
  echo "--- $pkg ---"
  grep -rEn "^\s*(from|import)\s+${pkg}(\.|$|\s)" demisto_sdk --include='*.py'
done

# 5. Bundling config
grep -rEn 'pyinstaller|PyInstaller|onefile|nuitka|shiv|pex' pyproject.toml
ls *.spec 2>/dev/null || echo "(no .spec files)"
```
