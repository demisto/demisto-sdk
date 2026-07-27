"""Runtime loader for UCC connector JSON schemas.

Reads `$UCC_SCHEMAS_DIR` (set by infra CI), stages schemas into a temp
dir, runs `datamodel-codegen` in-memory, and returns the generated
Pydantic modules keyed by schema stem. Nothing is written to the SDK
repo or site-packages.

Infra CI contract:
  * `<UCC>/schema/*.schema.json`               -> `$UCC_SCHEMAS_DIR/`
  * `<UCC>/schema/definitions/*.schema.json`   -> `$UCC_SCHEMAS_DIR/definitions/`
  * `export UCC_SCHEMAS_DIR=<absolute path>` before invoking the SDK.
  * Also install: `pip install 'datamodel-code-generator==0.25.9'`.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import shutil
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Optional, Tuple

from demisto_sdk.commands.common.logger import logger

# Pydantic v1 rejects these kwargs on `Field(...)` with a `List[...]`
# annotation ("field constraints are set but not enforced"), but
# datamodel-codegen 0.25.9 emits them anyway. Stripped post-codegen.
_UNENFORCED_LIST_FIELD_KWARGS: frozenset[str] = frozenset(
    {"min_items", "max_items", "min_length", "max_length", "unique_items"}
)

ENV_VAR = "UCC_SCHEMAS_DIR"

# sys.modules prefix for the runtime-generated modules.
_GENERATED_PACKAGE = (
    "demisto_sdk.commands.content_graph.strict_objects._runtime_generated"
)


class SchemaLoaderError(RuntimeError):
    """Raised when $UCC_SCHEMAS_DIR is misconfigured or codegen fails."""


def get_schemas_dir() -> Optional[Path]:
    """Return `$UCC_SCHEMAS_DIR` as a Path, or None if unset.

    Raises `SchemaLoaderError` if set but pointing at a non-existent path.
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


def _stage_schemas(src: Path) -> Tuple[Path, List[str]]:
    """Copy `*.schema.json` (and `definitions/`) into a fresh temp dir.

    Definitions are mirrored at both `<stage>/definitions/<name>` and
    `<stage>/<name>` so sibling and `definitions/`-prefixed `$ref`s both
    resolve. Only the *original* top-level schema filenames are returned;
    mirrored copies are excluded from codegen inputs.
    """
    stage = Path(tempfile.mkdtemp(prefix="ucc_schemas_"))
    top_level_names: List[str] = []
    for f in src.glob("*.schema.json"):
        shutil.copy(f, stage / f.name)
        top_level_names.append(f.name)
    defs = src / "definitions"
    if defs.is_dir():
        shutil.copytree(defs, stage / "definitions")
        for f in defs.glob("*.schema.json"):
            target = stage / f.name
            if not target.exists():
                shutil.copy(f, target)
    if not top_level_names:
        raise SchemaLoaderError(f"No *.schema.json files found in {src!r}.")
    return stage, sorted(top_level_names)


def _run_codegen(stage_dir: Path, out_dir: Path, top_level_names: List[str]) -> None:
    """Invoke `datamodel-codegen` per top-level staged schema.

    Per-file invocation with `cwd=stage_dir` avoids a datamodel-codegen
    0.25.9 bug where directory-mode resolves sibling `$ref`s against a
    mangled path. Definitions (mirrored to `stage_dir/`) are pulled in
    transitively via `$ref`s.
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
            "datamodel-code-generator is not installed. "
            "Install with: pip install 'datamodel-code-generator==0.25.9'"
        ) from exc

    if not top_level_names:
        raise SchemaLoaderError(f"No top-level schemas to codegen in {stage_dir!r}.")

    # 0.25.9 quirk: schemas w/o peer $refs want a `.py` file output;
    # schemas with peer $refs want a directory. Try file, fall back to
    # directory on the specific modular-refs error.
    original_cwd = Path.cwd()
    try:
        os.chdir(stage_dir)
        for name in top_level_names:
            stem = name[: -len(".schema.json")]
            file_out = out_dir / f"{stem}.py"
            try:
                generate(
                    input_=Path(name),
                    input_file_type=InputFileType.JsonSchema,
                    output=file_out,
                    output_model_type=DataModelType.PydanticBaseModel,
                    target_python_version=PythonVersion.PY_39,
                    use_schema_description=True,
                    use_default_kwarg=True,
                    reuse_model=True,
                )
            except Exception as exc:
                if "Modular references require an output directory" not in str(exc):
                    raise
                if file_out.exists():
                    file_out.unlink()
                pkg_out = out_dir / stem
                pkg_out.mkdir(parents=True, exist_ok=True)
                generate(
                    input_=Path(name),
                    input_file_type=InputFileType.JsonSchema,
                    output=pkg_out,
                    output_model_type=DataModelType.PydanticBaseModel,
                    target_python_version=PythonVersion.PY_39,
                    use_schema_description=True,
                    use_default_kwarg=True,
                    reuse_model=True,
                )
    finally:
        os.chdir(original_cwd)


def _annotation_is_list(node: Optional[ast.AST]) -> bool:
    """True if `node` is a `List[...]` / `Optional[List[...]]` annotation."""
    if node is None:
        return False
    if isinstance(node, ast.Subscript):
        value = node.value
        if isinstance(value, ast.Name) and value.id in {"List", "list"}:
            return True
        if isinstance(value, ast.Name) and value.id in {"Optional", "Union"}:
            slc = node.slice
            if isinstance(slc, ast.Tuple):
                return any(_annotation_is_list(elt) for elt in slc.elts)
            return _annotation_is_list(slc)
    return False


def _sanitize_generated_file(path: Path) -> bool:
    """Strip pydantic-v1 unenforced constraints from `List[...]` Field()s.

    See `_UNENFORCED_LIST_FIELD_KWARGS`. Returns True iff the file was modified.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    changed = False

    def _clean_field_call(call: ast.Call) -> bool:
        func = call.func
        is_field = (isinstance(func, ast.Name) and func.id == "Field") or (
            isinstance(func, ast.Attribute) and func.attr == "Field"
        )
        if not is_field:
            return False
        new_kwargs = [
            kw for kw in call.keywords if kw.arg not in _UNENFORCED_LIST_FIELD_KWARGS
        ]
        if len(new_kwargs) != len(call.keywords):
            call.keywords = new_kwargs
            return True
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and _annotation_is_list(node.annotation):
            value = node.value
            if isinstance(value, ast.Call) and _clean_field_call(value):
                changed = True

    if not changed:
        return False

    try:
        new_source = ast.unparse(tree)
    except AttributeError:
        # `ast.unparse` needs py3.9+; skip rather than corrupt.
        return False
    path.write_text(new_source, encoding="utf-8")
    return True


def _sanitize_generated_tree(out_dir: Path) -> None:
    """Run :func:`_sanitize_generated_file` on every generated `.py`."""
    for py in sorted(out_dir.rglob("*.py")):
        _sanitize_generated_file(py)


def _register_generated_modules(out_dir: Path) -> Dict[str, ModuleType]:
    """Import every generated `.py` under `out_dir` as a real module.

    Registers both per-file modules and per-schema `__init__.py` packages
    (codegen puts the root model in the latter when the schema has peer
    `$ref`s). Returns a dict keyed by schema stem.
    """
    out_dir_str = str(out_dir)
    if out_dir_str not in sys.path:
        sys.path.insert(0, out_dir_str)

    if _GENERATED_PACKAGE not in sys.modules:
        pkg = ModuleType(_GENERATED_PACKAGE)
        pkg.__path__ = [out_dir_str]  # type: ignore[attr-defined]
        sys.modules[_GENERATED_PACKAGE] = pkg

    modules: Dict[str, ModuleType] = {}
    for py in sorted(out_dir.rglob("*.py")):
        rel_parts = py.relative_to(out_dir).with_suffix("").parts
        is_init = py.name == "__init__.py"

        if is_init:
            pkg_parts = rel_parts[:-1]
            if not pkg_parts:
                continue
            qualname = ".".join([_GENERATED_PACKAGE, *pkg_parts])
            key = ".".join(pkg_parts)
            leaf_key = pkg_parts[-1]
        else:
            qualname = ".".join([_GENERATED_PACKAGE, *rel_parts])
            stem = rel_parts[-1]
            clean_stem = stem[: -len("_schema")] if stem.endswith("_schema") else stem
            key = (
                clean_stem
                if len(rel_parts) == 1
                else ".".join([*rel_parts[:-1], clean_stem])
            )
            leaf_key = clean_stem

        spec = importlib.util.spec_from_file_location(qualname, py)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        if is_init:
            mod.__path__ = [str(py.parent)]  # type: ignore[attr-defined]
        sys.modules[qualname] = mod
        spec.loader.exec_module(mod)

        modules[key] = mod
        modules.setdefault(leaf_key, mod)

    return modules


@lru_cache(maxsize=1)
def load_generated_modules() -> Dict[str, ModuleType]:
    """Discover UCC schemas and build in-memory Pydantic modules.

    Returns `{}` when `$UCC_SCHEMAS_DIR` is unset. Cached per process;
    call :func:`reset_cache` in tests that swap the env var mid-run.
    """
    src = get_schemas_dir()
    if src is None:
        logger.debug(f"${ENV_VAR} unset - strict connector validation skipped.")
        return {}

    stage, top_level_names = _stage_schemas(src)
    out_dir = Path(tempfile.mkdtemp(prefix="ucc_generated_"))
    try:
        _run_codegen(stage, out_dir, top_level_names)
    except SchemaLoaderError:
        raise
    except Exception as exc:
        raise SchemaLoaderError(
            f"datamodel-codegen failed while processing {src!r}: {exc}"
        ) from exc

    _sanitize_generated_tree(out_dir)
    modules = _register_generated_modules(out_dir)
    logger.debug(
        f"UCC schema loader: generated {len(modules)} Pydantic module(s) from {src}"
    )
    return modules


def get_generated_module(schema_stem: str) -> Optional[ModuleType]:
    """Return the generated module for `<schema_stem>.schema.json`, or None.

    Returns None when `$UCC_SCHEMAS_DIR` is unset (strict validation off).
    Re-raises `SchemaLoaderError` when the env var is set but codegen fails,
    to prevent silent false-green CI runs.
    """
    try:
        return load_generated_modules().get(schema_stem)
    except SchemaLoaderError:
        if get_schemas_dir() is None:
            return None
        raise


def reset_cache() -> None:
    """Drop the in-memory cache; next call re-runs codegen (tests only)."""
    load_generated_modules.cache_clear()
