"""
Typer CLI setup for the ``upload-custom-integration`` command.

Exposes exactly two user-facing flags:
  -i / --input    Path to the integration YAML file or directory.
  --force-id      Bypass the ``_copy`` marker check (with a warning).
                  **Not recommended** — omitting the ``_copy`` suffix risks
                  ID conflicts with official marketplace integrations.

All other upload options (marketplace, zip, insecure, etc.) are handled
internally by the core upload pipeline with its defaults.
"""

from pathlib import Path

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.upload.upload_custom_integration import (
    upload_custom_integration_entity,
)


@logging_setup_decorator
def upload_custom_integration(
    ctx: typer.Context,
    input_path: Path = typer.Option(
        ...,
        "--input",
        "-i",
        exists=True,
        resolve_path=True,
        help=(
            "Path to the integration YAML file or its parent directory. "
            "The file's 'commonfields.id' and 'name' must end with '_copy'. "
            "NOTE: It is also strongly recommended to append '_copy' to the "
            "integration's display name ('display' field) to avoid confusion "
            "with existing marketplace integrations in the UI."
        ),
    ),
    force_id: bool = typer.Option(
        False,
        "--force-id",
        help=(
            "Bypass the '_copy' marker validation. "
            "WARNING: Uploading without '_copy' risks conflicting with "
            "official marketplace IDs and may cause pack installation failures. "
            "Before using this flag, verify ALL of the following: "
            "(1) Your chosen ID is completely unique and does NOT match the original integration ID. "
            "(2) Your chosen ID does NOT match any other integration ID already present in the repository. "
            "(3) Your chosen ID does NOT match any integration ID published on the Marketplace."
        ),
    ),
    # The three options below are injected by @logging_setup_decorator and must
    # be present in the signature, but are hidden from --help output so the
    # user only sees -i/--input and --force-id.
    console_log_threshold: str = typer.Option(
        None, "--console-log-threshold", hidden=True
    ),
    file_log_threshold: str = typer.Option(None, "--file-log-threshold", hidden=True),
    log_file_path: str = typer.Option(None, "--log-file-path", hidden=True),
) -> None:
    """Upload a custom integration to Cortex Platform with '_copy' marker safety enforcement.

    Validates that the integration's 'commonfields.id' and 'name' fields end
    with the '_copy' marker before uploading, preventing ID conflicts with
    official marketplace integrations.

    \b
    RISK: If a custom integration is uploaded with an ID that matches a marketplace
    integration's ID, subsequent installations of the marketplace containing that
    integration will fail with a system error.

    \b
    ENVIRONMENT VARIABLES:
      DEMISTO_BASE_URL   Cortex Platform instance URL (required)
      DEMISTO_API_KEY    Valid API key for the instance (required)
      XSIAM_AUTH_ID      Auth ID for Cortex Platform (required)

    \b
    EXAMPLES:
      demisto-sdk upload-custom-integration -i Integrations/MyIntegration_copy/MyIntegration_copy.yml
      demisto-sdk upload-custom-integration -i Integrations/MyIntegration_copy/
      demisto-sdk upload-custom-integration -i Integrations/MyIntegration/MyIntegration.yml --force-id
    """
    upload_custom_integration_entity(
        input=input_path,
        force_id=force_id,
    )
