"""Runtime loader for UCC connector JSON schemas.

Reads `$UCC_SCHEMAS_DIR` (set by the infra CI job), stages the schemas
into a temp dir, runs `datamodel-codegen` in-memory, and returns the
generated Pydantic modules keyed by schema stem.

Nothing is written to the SDK repo or to installed site-packages.

Contract for the infra CI job:
  * `<UCC>/schema/*.schema.json`               -> `$UCC_SCHEMAS_DIR/`
  * `<UCC>/schema/definitions/*.schema.json`   -> `$UCC_SCHEMAS_DIR/definitions/`
  * `export UCC_SCHEMAS_DIR=<absolute path>` before invoking the SDK.
  * Also install: `pip install 'datamodel-code-generator==0.25.9'`.
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

from demisto_sdk.commands.common.logger import logger

ENV_VAR = "UCC_SCHEMAS_DIR"

# sys.modules prefix for the runtime-generated modules.
_GENERATED_PACKAGE = "demisto_sdk.commands.content_graph.strict_objects._runtime_generated"


class SchemaLoaderError(RuntimeError):
    """Raised when $UCC_SCHEMAS_DIR is misconfigured or codegen fails."""


def get_schemas_dir() -> Optional[Path]:
    """Return `$UCC_SCHEMAS_DIR` as a Path, or None if unset.

    Raises `SchemaLoaderError` if the env var is set but points at a
    non-existent path - infra misconfiguration must be noisy.
    """
    env_val = os.environ.get(ENV_VAR)
    if not env_val:
        return None
    candidate = Path(env_val).expanduser().resolve()
    if not candidate.is_dir():
        raise SchemaLoaderError(
            f"{ENV_VAR}={env_val!r} but the directory does not exist."
        )
    return candidate


def _stage_schemas(src: Path) -> Path:
    """Copy `*.schema.json` (and `definitions/`) into a fresh temp dir.

    Filters out README.md / .py so datamodel-codegen's directory walker
    doesn't try to parse them as JSON.
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
    """Invoke `datamodel-codegen` against the staged schemas."""
    try:
        from datamodel_code_generator import (
            DataModelType,
            InputFileType,
            PythonVersion,
            generate,
        )
    except ImportError as exc:
        raise SchemaLoaderError(
            "datamodel-code-generator is not installed. "
            "Install with: pip install 'datamodel-code-generator==0.25.9'"
        ) from exc

    # Pinned to 0.25.9: newer releases dropped the pydantic v1 output.
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

    Files under `definitions/` (from `$UCC_SCHEMAS_DIR/definitions/`) are
    picked up recursively. The returned dict is keyed by schema stem
    (`connector.schema.json` -> `"connector"`).
    """
    out_dir_str = str(out_dir)
    if out_dir_str not in sys.path:
        sys.path.insert(0, out_dir_str)

    # Register the parent package so relative imports resolve.
    if _GENERATED_PACKAGE not in sys.modules:
        pkg = ModuleType(_GENERATED_PACKAGE)
        pkg.__path__ = [out_dir_str]  # type: ignore[attr-defined]
        sys.modules[_GENERATED_PACKAGE] = pkg

    modules: Dict[str, ModuleType] = {}
    for py in sorted(out_dir.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        rel_parts = py.relative_to(out_dir).with_suffix("").parts
        qualname = ".".join([_GENERATED_PACKAGE, *rel_parts])

        spec = importlib.util.spec_from_file_location(qualname, py)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        sys.modules[qualname] = mod
        spec.loader.exec_module(mod)

        stem = py.stem
        clean_stem = stem[: -len("_schema")] if stem.endswith("_schema") else stem
        # Files under `definitions/` are keyed as `definitions.<stem>` AND
        # by their leaf name for convenience.
        key = clean_stem if len(rel_parts) == 1 else ".".join([*rel_parts[:-1], clean_stem])
        modules[key] = mod
        modules.setdefault(clean_stem, mod)

    return modules


@lru_cache(maxsize=1)
def load_generated_modules() -> Dict[str, ModuleType]:
    """Discover UCC schemas and build in-memory Pydantic modules.

    Returns `{}` when `$UCC_SCHEMAS_DIR` is unset. Cached per process;
    call :func:`reset_cache` in tests that swap the env var mid-run.
    """
    src = get_schemas_dir()
    if src is None:
        logger.info(
            f"[UCC-schema-loader] ${ENV_VAR} unset. Strict connector "
            "validation will be skipped."
        )
        return {}

    schema_files = sorted(src.glob("*.schema.json"))
    defs_files = (
        sorted((src / "definitions").glob("*.schema.json"))
        if (src / "definitions").is_dir()
        else []
    )
    logger.info(f"[UCC-schema-loader] resolving schemas from ${ENV_VAR}: {src}")
    logger.info(
        f"[UCC-schema-loader] discovered {len(schema_files)} top-level "
        f"schema(s) + {len(defs_files)} definitions/ file(s): "
        f"top={[f.name for f in schema_files]} "
        f"defs={[f.name for f in defs_files]}"
    )

    stage = _stage_schemas(src)
    out_dir = Path(tempfile.mkdtemp(prefix="ucc_generated_"))
    try:
        _run_codegen(stage, out_dir)
    except SchemaLoaderError:
        raise
    except Exception as exc:
        logger.error(
            f"[UCC-schema-loader] datamodel-codegen failed for {src!r}: {exc}"
        )
        raise SchemaLoaderError(
            f"datamodel-codegen failed while processing {src!r}: {exc}"
        ) from exc

    modules = _register_generated_modules(out_dir)
    logger.info(
        f"[UCC-schema-loader] generated {len(modules)} Pydantic module(s) "
        f"in-memory: {sorted(modules)}"
    )
    return modules


def get_generated_module(schema_stem: str) -> Optional[ModuleType]:
    """Return the generated module for `<schema_stem>.schema.json`, or None."""
    try:
        return load_generated_modules().get(schema_stem)
    except SchemaLoaderError:
        return None


def reset_cache() -> None:
    """Drop the in-memory cache; the next call re-runs codegen (tests only)."""
    load_generated_modules.cache_clear()
