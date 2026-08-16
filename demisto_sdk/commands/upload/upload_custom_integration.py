"""
Core logic for the ``upload-custom-integration`` command.

This module is a thin safety wrapper around the existing
:func:`~demisto_sdk.commands.upload.upload.upload_content_entity` function.
It enforces the ``_copy`` naming convention on integration IDs and display
names **before** delegating to the standard upload pipeline.

This command targets the **Cortex Platform marketplace exclusively**.
``marketplace="platform"`` is hardcoded in the call to
:func:`~demisto_sdk.commands.upload.upload.upload_content_entity` and cannot
be overridden.  Only ``-i`` / ``--input`` and ``--force-id`` are accepted as
user-facing flags; any other argument is rejected by the explicit function
signature.

The existing ``demisto-sdk upload`` command is **not modified** by this module.
"""

from pathlib import Path
from typing import Any

import typer

from demisto_sdk.commands.upload.integration_copy_validator import (
    is_integration_yaml,
    resolve_integration_yaml,
    validate_integration_copy_marker,
)

# The marketplace is fixed for this command — Cortex Platform only.
# Passing any other value to upload_content_entity is intentionally prevented
# by the explicit function signature (no marketplace parameter exposed).
_MARKETPLACE = "platform"


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
            high-visibility warning instead of raising an error.

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

    # Resolve directory → YAML file transparently so that both
    #   -i Integrations/MyIntegration_copy/
    #   -i Integrations/MyIntegration_copy/MyIntegration_copy.yml
    # work identically.
    resolved_path = resolve_integration_yaml(input_path)

    if not is_integration_yaml(resolved_path):
        raise typer.BadParameter(
            f"'{input_path}' does not appear to be an integration YAML "
            f"(missing 'commonfields' / 'script'+'category' keys). "
            "Use 'demisto-sdk upload' for packs and other content types."
        )

    validate_integration_copy_marker(resolved_path, force_id=force_id)

    # Delegate to the core upload pipeline.
    upload_content_entity(input=resolved_path, marketplace=_MARKETPLACE)
