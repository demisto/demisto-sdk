"""
Typer CLI setup for the ``upload-custom-integration`` command.

This module registers the ``upload-custom-integration`` subcommand with the
demisto-sdk Typer application.  It mirrors the parameter surface of the
standard ``upload`` command where applicable, but is intentionally scoped to
**single integration YAML files** and adds the ``--force-id`` safety flag.

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
            "Path to the integration YAML file to upload. "
            "Must be a single integration YAML (not a pack directory). "
            "The file's 'commonfields.id' and 'name' fields must end with "
            "the '_copy' suffix unless --force-id is passed."
        ),
    ),
    force_id: bool = typer.Option(
        False,
        "--force-id",
        help=(
            "Bypass the '_copy' marker validation and upload even if "
            "'commonfields.id' or 'name' do not end with '_copy'. "
            "WARNING: Uploading without the '_copy' marker risks conflicting "
            "with official system pack IDs and may cause system pack download "
            "failures. Use only when you are certain the ID is unique."
        ),
    ),
    xsiam: bool = typer.Option(
        False,
        "--xsiam",
        "-x",
        help="Upload the integration to the XSIAM server.",
    ),
    marketplace: str = typer.Option(
        None,
        "-mp",
        "--marketplace",
        help="The marketplace to which the content will be uploaded.",
    ),
    insecure: bool = typer.Option(
        False,
        "--insecure",
        help="Skip certificate validation.",
    ),
    override_existing: bool = typer.Option(
        False,
        "--override-existing",
        help=(
            "Skip the confirmation prompt when the integration is already "
            "installed on the target instance."
        ),
    ),
    console_log_threshold: str = typer.Option(
        None,
        "--console-log-threshold",
        help=(
            "Minimum logging threshold for console output. "
            "Possible values: DEBUG, INFO, SUCCESS, WARNING, ERROR."
        ),
    ),
    file_log_threshold: str = typer.Option(
        None,
        "--file-log-threshold",
        help="Minimum logging threshold for file output.",
    ),
    log_file_path: str = typer.Option(
        None,
        "--log-file-path",
        help="Path to save log files.",
    ),
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
      XSIAM_AUTH_ID      Auth ID for XSIAM or XSOAR 8.x instances (optional)

    \b
    EXAMPLES:
      # Upload a correctly named integration (happy path):
      demisto-sdk upload-custom-integration -i Integrations/MyIntegration_copy/MyIntegration_copy.yml

      # Force upload without the _copy marker (not recommended):
      demisto-sdk upload-custom-integration -i Integrations/MyIntegration/MyIntegration.yml --force-id

    Use ``demisto-sdk upload`` for general-purpose content uploads (packs,
    scripts, playbooks, etc.).
    """
    upload_custom_integration_entity(
        input=input_path,
        force_id=force_id,
        xsiam=xsiam,
        marketplace=marketplace,
        insecure=insecure,
        override_existing=override_existing,
        # Pass zip=False — single YAML files are not zipped.
        zip=False,
        tpb=False,
    )
