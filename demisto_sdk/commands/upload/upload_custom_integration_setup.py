"""
Typer CLI setup for the ``upload-custom-integration`` command.

Exposes exactly two user-facing flags:
  -i / --input    Path to the integration YAML file or directory.
  --force-id      Bypass the ``_copy`` marker check (with a warning).

All other upload options (marketplace, zip, insecure, etc.) are handled
internally by the core upload pipeline with its defaults.

The existing ``demisto-sdk upload`` command is **not modified** by this module.
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
            "The file's 'commonfields.id' and 'name' must end with '_copy' "
            "unless --force-id is passed."
        ),
    ),
    force_id: bool = typer.Option(
        False,
        "--force-id",
        help=(
            "Bypass the '_copy' marker validation. "
            "WARNING: Uploading without '_copy' risks conflicting with "
            "official system pack IDs and may cause download failures."
        ),
    ),
    # The three options below are injected by @logging_setup_decorator and must
    # be present in the signature, but are hidden from --help output so the
    # user only sees -i/--input and --force-id.
    console_log_threshold: str = typer.Option(None, "--console-log-threshold", hidden=True),
    file_log_threshold: str = typer.Option(None, "--file-log-threshold", hidden=True),
    log_file_path: str = typer.Option(None, "--log-file-path", hidden=True),
) -> None:
    """Upload a custom integration to Cortex XSOAR/XSIAM with safety enforcement.

    Validates that the integration's ``commonfields.id`` and ``name`` fields
    end with the ``_copy`` marker before uploading, preventing ID conflicts
    with official system pack integrations.

    \b
    RISK: If a custom integration is uploaded with an ID that matches a system
    integration's ID, subsequent downloads of the system pack containing that
    integration will fail with a system error.

    \b
    ENVIRONMENT VARIABLES:
      DEMISTO_BASE_URL   Cortex XSOAR/XSIAM instance URL (required)
      DEMISTO_API_KEY    Valid API key for the instance (required)
      XSIAM_AUTH_ID      Auth ID for XSIAM or XSOAR 8.x (optional)

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
