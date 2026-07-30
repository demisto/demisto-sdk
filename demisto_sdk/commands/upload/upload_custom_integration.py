"""
Core logic for the ``upload-custom-integration`` command.

This module acts as a thin wrapper around the existing
:func:`~demisto_sdk.commands.upload.upload.upload_content_entity` function.
It enforces the ``_copy`` naming convention on integration IDs and display
names **before** delegating to the standard upload pipeline.

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


def upload_custom_integration_entity(**kwargs: Any) -> None:
    """Validate the ``_copy`` marker then delegate to the core upload logic.

    This function is the entry point called by the Typer CLI setup in
    :mod:`~demisto_sdk.commands.upload.upload_custom_integration_setup`.

    Accepts both a direct ``.yml`` file path and an integration directory path
    (e.g., ``Packs/MyPack/Integrations/MyIntegration_copy/``).  When a
    directory is supplied, the single YAML file inside it is resolved
    automatically before validation and upload.

    Args:
        **kwargs: All keyword arguments accepted by
            :func:`~demisto_sdk.commands.upload.upload.upload_content_entity`,
            plus the additional ``force_id`` boolean flag.

    Raises:
        typer.BadParameter: When *input* is not an integration YAML (or a
            directory containing one), or when the ``_copy`` marker is missing
            and ``force_id`` is ``False``.
    """
    # Import here to mirror the lazy-import pattern used in upload.py and to
    # avoid circular imports at module load time.
    from demisto_sdk.commands.upload.upload import upload_content_entity

    input_val = kwargs.get("input")
    force_id: bool = kwargs.pop("force_id", False)

    # --- Guard 1: input must be provided ---
    if input_val is None:
        raise typer.BadParameter(
            "No input path provided. Use -i / --input to specify the integration YAML file."
        )

    input_path = Path(input_val)

    # Resolve directory → YAML file transparently so that both
    #   -i Integrations/MyIntegration_copy/
    #   -i Integrations/MyIntegration_copy/MyIntegration_copy.yml
    # work identically.
    resolved_path = resolve_integration_yaml(input_path)

    # --- Guard 2: must resolve to an integration YAML ---
    if not is_integration_yaml(resolved_path):
        raise typer.BadParameter(
            f"'{input_path}' does not appear to be an integration YAML "
            f"(missing 'commonfields' / 'script'+'category' keys). "
            "Use 'demisto-sdk upload' for packs and other content types."
        )

    # --- Guard 3: _copy marker validation ---
    validate_integration_copy_marker(resolved_path, force_id=force_id)

    # Propagate the resolved (file) path downstream so upload_content_entity
    # receives a concrete YAML path rather than a directory.
    kwargs["input"] = resolved_path

    # --- Delegate to the unchanged core upload pipeline ---
    upload_content_entity(**kwargs)
