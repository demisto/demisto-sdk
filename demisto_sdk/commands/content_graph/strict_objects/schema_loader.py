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

# Pydantic v1 raises `ValueError: ... field constraints are set but not
# enforced: <name>` at class-creation time when these kwargs appear on a
# `Field(...)` whose annotation is `List[...]` (especially with forward
# references / recursive models, e.g. triggers.ConditionGroup.children).
# datamodel-codegen 0.25.9 emits them anyway, so we strip them post-codegen.
# Keys mirror the pydantic v1 kwargs; both aliases are dropped defensively.
_UNENFORCED_LIST_FIELD_KWARGS: frozenset[str] = frozenset(
    {"min_items", "max_items", "min_length", "max_length", "unique_items"}
)

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


def _stage_schemas(src: Path) -> Tuple[Path, List[str]]:
    """Copy `*.schema.json` (and `definitions/`) into a fresh temp dir.

    Filters out README.md / .py so datamodel-codegen's directory walker
    doesn't try to parse them as JSON.

    Definitions are mirrored at BOTH `<stage>/definitions/<name>` and
    `<stage>/<name>` so that both `"$ref": "definitions/foo.schema.json"`
    and `"$ref": "foo.schema.json"` styles resolve at codegen time. The
    upstream UCC schemas use the sibling (`"$ref": "metadata.schema.json"`)
    style; the loader must not assume the `definitions/`-prefixed style.
    A top-level file with the same name is never clobbered.

    Returns `(stage_dir, top_level_names)` where `top_level_names` lists
    only the *original* top-level schema filenames (from `src/*.schema.json`).
    Mirrored `definitions/*.schema.json` copies are intentionally excluded:
    they exist purely to satisfy peer `$ref` resolution and must not be
    fed to codegen as inputs (that produces empty stub modules that
    collide with model files generated transitively from the real
    top-level schemas).
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
    """Invoke `datamodel-codegen` against each top-level staged schema.

    IMPORTANT: We invoke codegen per top-level schema file with `cwd` set
    to `stage_dir`, not once against the whole directory. Passing a
    directory to datamodel-codegen 0.25.9 triggers a bug where sibling
    `$ref`s (e.g. `"$ref": "metadata.schema.json"` from `connector.schema.json`)
    are resolved against a mangled path that walks `..` for every URI
    segment, producing `[Errno 2] No such file or directory:
    '<stage>/../../../../../../<abs-path>/metadata.schema.json'`.
    Per-file invocation with a stable cwd resolves peer refs correctly.

    Definitions files (already mirrored to `stage_dir/` by
    :func:`_stage_schemas`) are pulled in transitively via the top-level
    files' `$ref`s, so we do not need to codegen them separately.
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

    # Pinned to 0.25.9: newer releases dropped the pydantic v1 output.
    # One output namespace per input schema (either a `<name>.py` file for
    # schemas with no external `$ref`s, or a `<name>/` package when refs
    # produce submodules) so overlapping targets from different top-level
    # schemas don't collide on the same output filename.
    #
    # datamodel-codegen 0.25.9 quirk: for a schema with NO peer `$ref`s
    # it wants `output` to be a plain `.py` file and raises
    # `IsADirectoryError` if given a directory; for a schema WITH peer
    # `$ref`s it needs a directory to place the sibling submodules and
    # raises "Modular references require an output directory" otherwise.
    # We try file-mode first, retry as directory-mode on the specific
    # modular-refs error.
    original_cwd = Path.cwd()
    try:
        os.chdir(stage_dir)
        for name in top_level_names:
            # `<name>.schema.json` -> `<name>`; matches the public naming
            # used by `get_generated_module("connector")`.
            stem = name[: -len(".schema.json")]
            file_out = out_dir / f"{stem}.py"
            try:
                generate(
                    input_=Path(name),  # relative to cwd=stage_dir
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
                # Schema has peer `$ref`s -> retry with a package directory.
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
    """True if `node` is a `List[...]` / `list[...]` / `Optional[List[...]]`
    annotation (recursive), as emitted by datamodel-codegen 0.25.9.

    Handles the common shapes:
      * `List[X]`                  -> Subscript(Name("List"), ...)
      * `Optional[List[X]]`        -> Subscript(Name("Optional"), Subscript(...))
      * `Union[List[X], None]`     -> Subscript(Name("Union"), Tuple(...))
    """
    if node is None:
        return False
    if isinstance(node, ast.Subscript):
        value = node.value
        if isinstance(value, ast.Name) and value.id in {"List", "list"}:
            return True
        if isinstance(value, ast.Name) and value.id in {"Optional", "Union"}:
            slc = node.slice
            # py3.9+: slice is the expression directly, not an ast.Index.
            if isinstance(slc, ast.Tuple):
                return any(_annotation_is_list(elt) for elt in slc.elts)
            return _annotation_is_list(slc)
    return False


def _sanitize_generated_file(path: Path) -> bool:
    """Strip pydantic-v1 unenforced constraints from `List[...]` Field()s.

    datamodel-codegen 0.25.9 emits things like::

        children: List[ConditionNode] = Field(..., min_items=1)

    which pydantic v1 rejects at class-creation time because it cannot
    enforce `min_items` on that annotation shape (see
    `_UNENFORCED_LIST_FIELD_KWARGS`). We rewrite the file in place,
    dropping only the offending kwargs from `Field(...)` calls whose
    target annotation is a `List[...]`. All other lines are preserved.

    Returns True iff the file was modified.
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
        """Drop unenforced kwargs from a `Field(...)` call; True if changed."""
        func = call.func
        is_field = (
            (isinstance(func, ast.Name) and func.id == "Field")
            or (isinstance(func, ast.Attribute) and func.attr == "Field")
        )
        if not is_field:
            return False
        new_kwargs = [
            kw for kw in call.keywords
            if kw.arg not in _UNENFORCED_LIST_FIELD_KWARGS
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
        # `ast.unparse` requires py3.9+. Loader already targets 3.9+, but
        # if unparse is unavailable we skip rather than corrupt the file.
        return False
    path.write_text(new_source, encoding="utf-8")
    logger.debug(
        f"[UCC-schema-loader] sanitized unenforced List Field constraints "
        f"in {path}"
    )
    return True


def _sanitize_generated_tree(out_dir: Path) -> None:
    """Run :func:`_sanitize_generated_file` on every generated `.py`."""
    for py in sorted(out_dir.rglob("*.py")):
        _sanitize_generated_file(py)


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
    # First pass: register every non-__init__ generated module. These are the
    # `$ref` targets that codegen emitted as separate files (e.g. a
    # widget.schema.json that $refs tag.schema.json produces `widget/tag.py`
    # containing the Tag model).
    # Second pass (below): register each per-schema `__init__.py` under the
    # subdir name (e.g. `widget/__init__.py` -> key `"widget"`). Codegen
    # places the top-level schema's root model there when the schema has
    # `$ref`s to peer files, so we MUST NOT skip __init__.py or the caller
    # (`get_generated_module("connector")`) will see None even though codegen
    # succeeded.
    for py in sorted(out_dir.rglob("*.py")):
        rel_parts = py.relative_to(out_dir).with_suffix("").parts
        is_init = py.name == "__init__.py"

        if is_init:
            # `<subdir>/__init__.py` -> parts = ("<subdir>", "__init__");
            # keep only the subdir(s) so qualname is the package.
            pkg_parts = rel_parts[:-1]
            if not pkg_parts:
                # Root-level __init__.py (shouldn't exist here, defensive).
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
        # Packages need __path__ so their submodules import cleanly.
        if is_init:
            mod.__path__ = [str(py.parent)]  # type: ignore[attr-defined]
            sys.modules[qualname] = mod
        else:
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

    stage, top_level_names = _stage_schemas(src)
    out_dir = Path(tempfile.mkdtemp(prefix="ucc_generated_"))
    try:
        _run_codegen(stage, out_dir, top_level_names)
    except SchemaLoaderError:
        raise
    except Exception as exc:
        logger.error(
            f"[UCC-schema-loader] datamodel-codegen failed for {src!r}: {exc}"
        )
        raise SchemaLoaderError(
            f"datamodel-codegen failed while processing {src!r}: {exc}"
        ) from exc

    # Post-codegen: strip pydantic-v1 unenforced List Field kwargs (e.g.
    # `min_items=1` on `List[ConditionNode]`) that would otherwise raise
    # `ValueError: ... field constraints are set but not enforced` at
    # module import time in `_register_generated_modules` below.
    _sanitize_generated_tree(out_dir)

    modules = _register_generated_modules(out_dir)
    logger.info(
        f"[UCC-schema-loader] generated {len(modules)} Pydantic module(s) "
        f"in-memory: {sorted(modules)}"
    )
    return modules


def get_generated_module(schema_stem: str) -> Optional[ModuleType]:
    """Return the generated module for `<schema_stem>.schema.json`, or None.

    Behaviour:
      * `$UCC_SCHEMAS_DIR` unset -> return None (strict validation is off,
        by design; the SDK runs in non-strict mode).
      * `$UCC_SCHEMAS_DIR` set + codegen fails -> re-raise. The operator
        opted in to strict validation; silently degrading would produce
        false-green CI runs where `demisto-sdk validate` reports success
        while never actually running the strict-connector validators.
    """
    try:
        return load_generated_modules().get(schema_stem)
    except SchemaLoaderError:
        if get_schemas_dir() is None:
            return None
        raise


def reset_cache() -> None:
    """Drop the in-memory cache; the next call re-runs codegen (tests only)."""
    load_generated_modules.cache_clear()
