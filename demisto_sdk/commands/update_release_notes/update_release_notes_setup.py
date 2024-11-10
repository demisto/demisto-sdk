import sys
from pathlib import Path

import typer

from demisto_sdk.commands.common.constants import SDK_OFFLINE_ERROR_MESSAGE
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.common.tools import is_sdk_defined_working_offline
from demisto_sdk.utils.utils import update_command_args_from_config_file


@logging_setup_decorator
def update_release_notes(
    ctx: typer.Context,
    input: str = typer.Option(
        None, help="The relative path of the content pack. For example Packs/Pack_Name"
    ),
    update_type: str = typer.Option(
        None,
        help="The type of update being done. [major, minor, revision, documentation]",
        metavar="UPDATE_TYPE",
    ),
    version: str = typer.Option(None, help="Bump to a specific version."),
    use_git: bool = typer.Option(
        False,
        help="Use git to identify the relevant changed files, will be used by default if '-i' is not set.",
    ),
    force: bool = typer.Option(
        False, help="Force update release notes for a pack (even if not required)."
    ),
    text: str = typer.Option(
        None, help="Text to add to all of the release notes files."
    ),
    prev_ver: str = typer.Option(
        None, help="Previous branch or SHA1 commit to run checks against."
    ),
    pre_release: bool = typer.Option(
        False,
        help="Indicates that this change should be designated a pre-release version.",
    ),
    id_set_path: Path = typer.Option(
        None, help="The path of the id-set.json used for APIModule updates."
    ),
    breaking_changes: bool = typer.Option(
        False, help="If new version contains breaking changes."
    ),
    console_log_threshold: str = typer.Option(
        None,
        "--console-log-threshold",
        help="Minimum logging threshold for console output. Possible values: DEBUG, INFO, SUCCESS, WARNING, ERROR.",
    ),
    file_log_threshold: str = typer.Option(
        None, "--file-log-threshold", help="Minimum logging threshold for file output."
    ),
    log_file_path: str = typer.Option(
        None, "--log-file-path", help="Path to save log files."
    ),
):
    """Auto-increment pack version and generate release notes template."""
    from demisto_sdk.commands.update_release_notes.update_rn_manager import (
        UpdateReleaseNotesManager,
    )

    if is_sdk_defined_working_offline():
        typer.echo(SDK_OFFLINE_ERROR_MESSAGE, err=True)
        sys.exit(1)

    update_command_args_from_config_file("update-release-notes", locals())

    if force and input is None:
        typer.echo(
            "<red>Please add a specific pack in order to force a release notes update.</red>"
        )
        sys.exit(0)

    if not use_git and input is None:
        if not typer.confirm(
            "No specific pack was given, do you want to update all changed packs?"
        ):
            sys.exit(0)

    try:
        rn_mng = UpdateReleaseNotesManager(
            user_input=input,
            update_type=update_type,
            pre_release=pre_release,
            is_all=use_git,
            text=text,
            specific_version=version,
            id_set_path=id_set_path,
            prev_ver=prev_ver,
            is_force=force,
            is_bc=breaking_changes,
        )
        rn_mng.manage_rn_update()
        sys.exit(0)
    except Exception as e:
        typer.echo(
            f"<red>An error occurred while updating the release notes: {str(e)}</red>"
        )
        sys.exit(1)
