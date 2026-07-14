"""Runtime loader for UCC connector JSON schemas.

Design intent
-------------
The SDK does NOT ship the UCC (Unified Content Connectors) JSON schemas in
its own repo. Instead, the *infra* CI job that runs the SDK is expected to
drop the schemas onto disk at a well-known location and export the path via
the `UCC_SCHEMAS_DIR` environment variable. This module discovers those
schemas and generates Pydantic v1 model classes for them **in memory**, so:

- Zero commits to the demisto-sdk repo when UCC schemas change upstream.
- Zero on-disk artifacts written by the SDK at runtime.
- Any file the infra CI drops in (top-level `*.schema.json` or files under
  the `definitions/` subfolder for cross-file `$ref` resolution) becomes a
  live Pydantic model that the strict validation and graph object layers
  can consume.

Contract for the infra CI job
-----------------------------
1. Copy every `<UCC>/schema/*.schema.json` into `${UCC_SCHEMAS_DIR}/`.
2. Copy every `<UCC>/schema/definitions/*.schema.json` into
   `${UCC_SCHEMAS_DIR}/definitions/` (preserve the subfolder).
3. Do NOT rename files or edit JSON. The generated Python class names are
   derived from the filenames (`connector.schema.json` -> `ConnectorYaml`).
4. Export `UCC_SCHEMAS_DIR=<that absolute path>` before invoking the SDK.

Fallback for local dev / test
-----------------------------
If `UCC_SCHEMAS_DIR` is unset, we fall back to the schemas committed under
`strict_objects/schemas/` in this repo (currently just `connector.schema.json`).
That keeps `pytest`, local runs, and IDE type-checking working out of the box.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Dict, Optional

# Environment variable the infra CI job sets to point at the UCC schemas dir.
ENV_VAR = "UCC_SCHEMAS_DIR"

# Default (dev/test) fallback: the committed `schemas/` folder in this repo.
_DEFAULT_FALLBACK_DIR = Path(__file__).parent / "schemas"

# Prefix used when registering generated modules in `sys.modules` so they
# behave like normal importable packages (needed for `TypeAdapter`, pickle,
# and any tooling that walks module qualnames).
_GENERATED_PACKAGE = "demisto_sdk.commands.content_graph.strict_objects._runtime_generated"


class SchemaLoaderError(RuntimeError):
    """Raised when the schemas dir is missing, empty, or codegen fails."""


def get_schemas_dir() -> Optional[Path]:
    """Return the directory holding UCC schemas, or `None` if unavailable.

    Resolution order:
        1. `$UCC_SCHEMAS_DIR` if set and points to an existing directory.
        2. The committed `strict_objects/schemas/` folder if it contains at
           least one `*.schema.json` file.
        3. `None` -> caller should skip validation gracefully.
    """
    env_val = os.environ.get(ENV_VAR)
    if env_val:
        candidate = Path(env_val).expanduser().resolve()
        if candidate.is_dir():
            return candidate
        # Explicit env var but bad path is a hard error: infra CI is
        # miswired and we want that to be noisy, not silently skipped.
        raise SchemaLoaderError(
            f"{ENV_VAR}={env_val!r} but the directory does not exist."
        )

    if _DEFAULT_FALLBACK_DIR.is_dir() and any(
        _DEFAULT_FALLBACK_DIR.glob("*.schema.json")
    ):
        return _DEFAULT_FALLBACK_DIR

    return None


def _stage_schemas(src: Path) -> Path:
    """Copy `*.schema.json` (and `definitions/`) into a fresh temp dir.

    `datamodel-code-generator` iterates every file in the input directory,
    so we exclude README.md, `.py`, and other non-JSON siblings that would
    otherwise confuse the loader.
    """
    stage = Path(tempfile.mkdtemp(prefix="ucc_schemas_"))
    for f in src.glob("*.schema.json"):
        shutil.copy(f, stage / f.name)
    defs = src / "definitions"
    if defs.is_dir():
        shutil.copytree(defs, stage / "definitions")
    if not any(stage.glob("*.schema.json")):
        raise SchemaLoaderError(f"No *.schema.json files found in {src!r}.")
    return stage


def _run_codegen(stage_dir: Path, out_dir: Path) -> None:
    """Invoke datamodel-codegen against the staged schemas.

    We defer the import so environments that never trigger connector
    validation do not pay the dependency cost at SDK import time.
    """
    try:
        from datamodel_code_generator import (
            DataModelType,
            InputFileType,
            PythonVersion,
            generate,
        )
    except ImportError as exc:
        raise SchemaLoaderError(
            "datamodel-code-generator is not installed. Install with:\n"
            "    pip install 'datamodel-code-generator==0.25.9'\n"
            "(0.26+ dropped pydantic v1 output; the SDK is on pydantic v1.)"
        ) from exc

    # Note: keyword names match `datamodel_code_generator.generate()` (Python
    # API), which differ slightly from the CLI flags (e.g. `use_default_kwarg`
    # vs `--use-default`).
    generate(
        input_=stage_dir,
        input_file_type=InputFileType.JsonSchema,
        output=out_dir,
        output_model_type=DataModelType.PydanticBaseModel,
        target_python_version=PythonVersion.PY_39,
        use_schema_description=True,
        use_default_kwarg=True,
        reuse_model=True,
    )


def _register_generated_modules(out_dir: Path) -> Dict[str, ModuleType]:
    """Import every generated `.py` file under `out_dir` as a real module.

    Registers them under `_GENERATED_PACKAGE.<stem>` in `sys.modules` so
    downstream code can import them by name if needed. Returns a mapping
    from schema stem (e.g. `"connector"`) to the imported module.
    """
    # Make sure the generated output dir is on sys.path exactly once.
    out_dir_str = str(out_dir)
    if out_dir_str not in sys.path:
        sys.path.insert(0, out_dir_str)

    # Ensure the parent package exists in sys.modules so relative imports
    # inside generated files resolve when datamodel-codegen emits them.
    if _GENERATED_PACKAGE not in sys.modules:
        pkg = ModuleType(_GENERATED_PACKAGE)
        pkg.__path__ = [out_dir_str]  # type: ignore[attr-defined]
        sys.modules[_GENERATED_PACKAGE] = pkg

    modules: Dict[str, ModuleType] = {}
    # Walk recursively so files that datamodel-codegen emits under
    # `definitions/` (mirroring the schemas layout) are also picked up.
    for py in sorted(out_dir.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        stem = py.stem  # e.g. "connector_schema"
        # Preserve the subfolder in the qualname so `definitions/tag_schema.py`
        # becomes `<pkg>.definitions.tag_schema` and cannot collide with a
        # top-level module.
        rel_parts = py.relative_to(out_dir).with_suffix("").parts
        qualname = ".".join([_GENERATED_PACKAGE, *rel_parts])

        # Load the module fresh so subsequent reloads (e.g. tests that
        # point UCC_SCHEMAS_DIR at a different fixture) always pick up
        # the current codegen output.
        spec = importlib.util.spec_from_file_location(qualname, py)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        sys.modules[qualname] = mod
        spec.loader.exec_module(mod)

        # Normalize the key: strip the `_schema` suffix so callers can look
        # up modules by the schema stem (`connector`, `tag`, ...). For
        # subfolder modules the key is prefixed with the subfolder name
        # (e.g. `definitions.tag`) to avoid ambiguity.
        clean_stem = stem[: -len("_schema")] if stem.endswith("_schema") else stem
        if len(rel_parts) == 1:
            key = clean_stem
        else:
            key = ".".join([*rel_parts[:-1], clean_stem])
        modules[key] = mod
        # Also register a short alias for top-level lookups by leaf name so
        # callers can still ask for e.g. `get_generated_module("tag")` even
        # when the file lives under `definitions/`.
        modules.setdefault(clean_stem, mod)

    return modules


@lru_cache(maxsize=1)
def load_generated_modules() -> Dict[str, ModuleType]:
    """Discover UCC schemas and build in-memory Pydantic modules for them.

    Cached: the first call performs the codegen; subsequent calls in the
    same process reuse the result. Call :func:`reset_cache` after moving
    the schemas dir at runtime (mainly useful in tests).

    Returns an empty dict if no schemas dir is available so callers can
    degrade gracefully to a no-op.
    """
    src = get_schemas_dir()
    if src is None:
        return {}

    stage = _stage_schemas(src)
    out_dir = Path(tempfile.mkdtemp(prefix="ucc_generated_"))
    try:
        _run_codegen(stage, out_dir)
    except SchemaLoaderError:
        raise
    except Exception as exc:
        raise SchemaLoaderError(
            f"datamodel-codegen failed while processing {src!r}: {exc}"
        ) from exc

    return _register_generated_modules(out_dir)


def get_generated_module(schema_stem: str) -> Optional[ModuleType]:
    """Return the generated module for `<schema_stem>.schema.json`, or None.

    Example:
        >>> get_generated_module("connector")  # -> module for connector.schema.json
    """
    try:
        return load_generated_modules().get(schema_stem)
    except SchemaLoaderError:
        return None


def reset_cache() -> None:
    """Clear the in-memory cache; the next call re-runs codegen.

    Mainly useful for tests that swap `UCC_SCHEMAS_DIR` mid-run.
    """
    load_generated_modules.cache_clear()
