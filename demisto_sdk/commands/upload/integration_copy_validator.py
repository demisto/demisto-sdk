"""
Validation logic for the upload-custom-integration command.

Enforces the '_copy' marker naming convention on integration IDs and
name before upload, preventing ID conflicts with official system pack integrations.

Background
----------
If a custom integration is uploaded with an ``id`` that matches a system
integration's ``id``, any subsequent attempt to install the system pack that
contains that integration will fail with a system error.  The ``_copy`` suffix
is the established convention that distinguishes custom (user-owned)
copies from system-managed originals.
"""

from pathlib import Path

import typer
from ruamel.yaml import YAMLError

from demisto_sdk.commands.common.logger import logger

# The required suffix that marks an integration as a user-owned copy.
COPY_MARKER: str = "_copy"

_COPY_MARKER_RISK_EXPLANATION: str = (
    "Uploading a custom integration whose ID matches a system integration ID "
    "will cause subsequent installations of the system pack that contains that "
    "integration to fail with a system error."
)

# YAML key path for the canonical integration ID.
_COMMONFIELDS_KEY = "commonfields"
_ID_KEY = "id"
_NAME_KEY = "name"


def _load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents as a dict."""
    from demisto_sdk.commands.common.handlers import YAML_Handler

    yaml = YAML_Handler()
    with path.open("r", encoding="utf-8") as fh:
        return yaml.load(fh) or {}


def resolve_integration_yaml(path: Path) -> Path:
    """If *path* is a directory, resolve the single integration YAML file inside it.

    Users often pass the integration folder (e.g.,
    ``-i Packs/MyPack/Integrations/MyIntegration_copy/``) rather than the
    explicit ``.yml`` file path.  This helper transparently handles both forms.

    Args:
        path: A filesystem path that may be either a file or a directory.

    Returns:
        The resolved ``.yml`` / ``.yaml`` file path when *path* is a directory
        containing exactly one non-hidden YAML file; otherwise *path* unchanged.

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
    """Return ``True`` if *path* points to an integration YAML file (or a
    directory containing exactly one integration YAML).

    Detection is based on the presence of the ``commonfields`` key, which is
    present in integration YAMLs but not in playbooks, scripts, or other
    content types.  As a secondary signal, the presence of both ``script`` and
    ``category`` keys (used in unified integration YAMLs) is also accepted.

    Args:
        path: Filesystem path to the YAML file or integration directory.

    Returns:
        ``True`` when the file looks like an integration YAML, ``False``
        otherwise (including when the file cannot be read or parsed).
    """
    target_path = resolve_integration_yaml(path)
    if not target_path.is_file():
        return False
    try:
        data = _load_yaml(target_path)
        return _COMMONFIELDS_KEY in data or ("script" in data and "category" in data)
    except OSError:
        # File exists (checked above) but cannot be read — treat as non-integration.
        return False
    except YAMLError as exc:
        raise typer.BadParameter(
            f"YAML syntax error in '{target_path}': {exc}"
        ) from exc


def _read_id_and_name(path: Path) -> tuple[str, str]:
    """Read ``commonfields.id`` (with top-level ``id`` fallback) and ``name``
    from an integration YAML.

    Args:
        path: Path to the integration YAML file or its parent directory.

    Returns:
        A ``(integration_id, integration_name)`` tuple.

    Raises:
        typer.BadParameter: When the YAML cannot be parsed or the expected
            fields are missing.
    """
    target_path = resolve_integration_yaml(path)
    try:
        data = _load_yaml(target_path)
    except Exception as exc:
        raise typer.BadParameter(
            f"Could not parse YAML file '{target_path}': {exc}"
        ) from exc

    # Primary: commonfields.id (standard integration YAML structure).
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
            f"'commonfields.id' (or top-level 'id') is missing or empty in '{target_path}'."
        )
    if not integration_name:
        raise typer.BadParameter(f"'name' is missing or empty in '{target_path}'.")

    return integration_id, integration_name


def validate_integration_copy_marker(
    integration_yaml_path: Path,
    force_id: bool = False,
) -> None:
    """Validate that the integration YAML uses the ``_copy`` naming convention.

    Reads ``commonfields.id`` (with top-level ``id`` fallback) and ``name``
    from *integration_yaml_path* and checks that both values end with
    :data:`COPY_MARKER` (``"_copy"``).

    Args:
        integration_yaml_path: Path to the integration YAML file or its parent
            directory.
        force_id: When ``True``, skip the hard error and emit a high-visibility
            warning instead, then allow the upload to proceed.

    Raises:
        typer.BadParameter: When either field is missing the ``_copy`` suffix
            **and** *force_id* is ``False``.
    """
    integration_id, integration_name = _read_id_and_name(integration_yaml_path)

    id_ok = integration_id.endswith(COPY_MARKER)
    name_ok = integration_name.endswith(COPY_MARKER)

    if id_ok and name_ok:
        # Happy path — nothing to do.
        return

    missing_fields = []
    if not id_ok:
        missing_fields.append(f"commonfields.id = '{integration_id}'")
    if not name_ok:
        missing_fields.append(f"name = '{integration_name}'")

    missing_summary = " and ".join(missing_fields)

    if force_id:
        logger.warning(
            f"[WARNING] {_COPY_MARKER_RISK_EXPLANATION} "
            f"The following field(s) are missing the '{COPY_MARKER}' suffix: "
            f"{missing_summary}. "
            "Proceeding because --force-id was explicitly set."
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
        f"    demisto-sdk upload-custom-integration -i <path/to/integration.yml> --force-id\n"
    )
