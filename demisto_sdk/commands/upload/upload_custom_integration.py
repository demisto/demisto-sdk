"""
Core logic for the ``upload-custom-integration`` command.

This module is a thin safety wrapper around the existing
:func:`~demisto_sdk.commands.upload.upload.upload_content_entity` function.
It enforces the ``_copy`` naming convention on integration IDs and
name **before** delegating to the standard upload pipeline.

This command targets the **Cortex Platform marketplace exclusively**.
``marketplace="platform"`` is hardcoded in the call to
:func:`~demisto_sdk.commands.upload.upload.upload_content_entity` and cannot
be overridden.  Only ``-i`` / ``--input`` and ``--force-id`` are accepted as
user-facing flags; any other argument is rejected by the explicit function
signature.

Background
----------
If a custom integration is uploaded with an ``id`` that matches a marketplace
integration's ``id``, any subsequent attempt to install the pack that
contains that integration will fail with a system error.  The ``_copy`` suffix
is the established convention that distinguishes custom (user-owned)
copies from system-managed originals.
"""

from pathlib import Path
from typing import Any

import typer

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_yaml

# The marketplace is fixed for this command — Cortex Platform only.
_MARKETPLACE = "platform"

# The required suffix that marks an integration as a user-owned copy.
COPY_MARKER: str = "_copy"

_COPY_MARKER_RISK_EXPLANATION: str = (
    "Uploading a custom integration whose ID matches a marketplace integration ID "
    "will cause subsequent installations of the pack that contains that "
    "integration to fail with a system error."
)

_FORCE_ID_ACTIONABLE_GUIDANCE: str = (
    "ACTION REQUIRED — before continuing, verify ALL of the following:\n"
    "  1. Your chosen ID is completely unique and does NOT match the original integration ID.\n"
    "  2. Your chosen ID does NOT match any other integration ID already present in the repository.\n"
    "  3. Your chosen ID does NOT match any integration ID published on the Marketplace."
)

# YAML key path for the canonical integration ID.
_COMMONFIELDS_KEY = "commonfields"
_ID_KEY = "id"
_NAME_KEY = "name"


def resolve_integration_yaml(path: Path) -> Path:
    """If *path* is a directory, resolve the single integration YAML inside it.

    Accepts either a direct ``.yml`` file path or an integration directory.

    Raises:
        typer.BadParameter: When *path* is a directory containing more than one
            YAML file — the caller must specify the exact file path.
    """
    if path.is_file():
        return path
    if path.is_dir():
        yml_files = [
            f
            for f in list(path.glob("*.yml")) + list(path.glob("*.yaml"))
            if not f.name.startswith(".")
        ]
        if len(yml_files) == 1:
            return yml_files[0]
        if len(yml_files) > 1:
            names = ", ".join(f.name for f in sorted(yml_files))
            raise typer.BadParameter(
                f"'{path}' contains multiple YAML files ({names}). "
                "Pass the exact integration YAML file path with -i/--input."
            )
    # Return as-is; downstream checks will produce the appropriate error.
    return path


def is_integration_yaml(path: Path) -> bool:
    """Return ``True`` if *path* points to an integration YAML file.

    Detection is based on the presence of the ``commonfields`` key, which is
    present in all integration YAMLs (both split and unified forms).

    Returns ``False`` when the file cannot be read or parsed.
    """
    if not path.is_file():
        return False
    try:
        data = get_yaml(path) or {}
        return _COMMONFIELDS_KEY in data
    except OSError:
        return False
    except Exception as exc:
        raise typer.BadParameter(f"YAML syntax error in '{path}': {exc}") from exc


def validate_integration_copy_marker(
    integration_yaml_path: Path,
    force_id: bool = False,
) -> None:
    """Validate that the integration YAML uses the ``_copy`` naming convention.

    Reads ``commonfields.id`` and ``name`` from *integration_yaml_path* and
    checks that both values end with :data:`COPY_MARKER` (``"_copy"``).

    Args:
        integration_yaml_path: Path to the resolved integration YAML file.
        force_id: When ``True``, skip the hard error and emit a high-visibility
            warning with actionable guidance.

    Raises:
        typer.BadParameter: When either field is missing the ``_copy`` suffix
            **and** *force_id* is ``False``.
    """
    try:
        data = get_yaml(integration_yaml_path) or {}
    except Exception as exc:
        raise typer.BadParameter(
            f"Could not parse YAML file '{integration_yaml_path}': {exc}"
        ) from exc

    commonfields = data.get(_COMMONFIELDS_KEY, {})
    integration_id: str = ""
    if isinstance(commonfields, dict):
        integration_id = commonfields.get(_ID_KEY, "")
    # Fallback: top-level id (unified / marketplace-specific YAMLs).
    if not integration_id:
        integration_id = data.get(_ID_KEY, "")

    integration_name: str = data.get(_NAME_KEY, "")

    if not integration_id:
        raise typer.BadParameter(
            f"'commonfields.id' (or top-level 'id') is missing or empty in '{integration_yaml_path}'."
        )
    if not integration_name:
        raise typer.BadParameter(
            f"'name' is missing or empty in '{integration_yaml_path}'."
        )

    id_ok = integration_id.endswith(COPY_MARKER)
    name_ok = integration_name.endswith(COPY_MARKER)

    if id_ok and name_ok:
        return

    missing_fields = []
    if not id_ok:
        missing_fields.append(f"commonfields.id = '{integration_id}'")
    if not name_ok:
        missing_fields.append(f"name = '{integration_name}'")

    missing_summary = " and ".join(missing_fields)

    if force_id:
        logger.warning(
            f"<yellow>[WARNING] {_COPY_MARKER_RISK_EXPLANATION} "
            f"The following field(s) are missing the '{COPY_MARKER}' suffix: "
            f"{missing_summary}.\n"
            f"<red>{_FORCE_ID_ACTIONABLE_GUIDANCE}</red>\n"
            f"Proceeding because --force-id was explicitly set.</yellow>"
        )
        return

    raise typer.BadParameter(
        f"\n"
        f"  Integration field(s) missing the '{COPY_MARKER}' marker:\n"
        f"    {missing_summary}\n"
        f"\n"
        f"  RISK: {_COPY_MARKER_RISK_EXPLANATION}\n"
        f"\n"
        f"  Fix: Rename 'commonfields.id' and 'name' in your YAML to end with\n"
        f"  '{COPY_MARKER}' (e.g., 'MyIntegration{COPY_MARKER}'), then re-run:\n"
        f"\n"
        f"    demisto-sdk upload-custom-integration -i <path/to/integration.yml>\n"
        f"\n"
        f"  To bypass this check (not recommended), pass --force-id:\n"
        f"\n"
        f"  {_FORCE_ID_ACTIONABLE_GUIDANCE}\n"
        f"\n"
        f"    demisto-sdk upload-custom-integration -i <path/to/integration.yml> --force-id\n"
    )


def upload_custom_integration_entity(
    input: Any,
    force_id: bool = False,
) -> None:
    """Validate the ``_copy`` marker then delegate to the core upload logic.

    Accepts both a direct ``.yml`` file path and an integration directory path
    (e.g., ``Packs/MyPack/Integrations/MyIntegration_copy/``).  When a
    directory is supplied, the single YAML file inside it is resolved
    automatically before validation and upload.

    The upload always targets the **Cortex Platform marketplace**
    (``marketplace="platform"``).  This is hardcoded and cannot be changed
    by the caller.

    Args:
        input: Path to the integration YAML file or its parent directory.
        force_id: When ``True``, bypass the ``_copy`` marker check and emit a
            high-visibility warning with actionable guidance.

    Raises:
        typer.BadParameter: When *input* is not an integration YAML (or a
            directory containing one), or when the ``_copy`` marker is missing
            and ``force_id`` is ``False``.
    """
    # Import here to mirror the lazy-import pattern used in upload.py and to
    # avoid circular imports at module load time.
    from demisto_sdk.commands.upload.upload import upload_content_entity

    if input is None:
        raise typer.BadParameter(
            "No input path provided. Use -i / --input to specify the integration YAML file."
        )

    input_path = Path(input)

    # Resolve directory → YAML file once; all subsequent calls receive the
    # resolved file path directly so the file is not re-resolved internally.
    resolved_path = resolve_integration_yaml(input_path)

    if not is_integration_yaml(resolved_path):
        raise typer.BadParameter(
            f"'{input_path}' does not appear to be an integration YAML. "
            "Use 'demisto-sdk upload' for packs and other content types."
        )

    validate_integration_copy_marker(resolved_path, force_id=force_id)

    # Delegate to the core upload pipeline.
    upload_content_entity(input=resolved_path, marketplace=_MARKETPLACE)
