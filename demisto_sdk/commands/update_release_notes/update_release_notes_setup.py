from pathlib import Path
from typing import Optional

import typer

from demisto_sdk.commands.common.constants import SDK_OFFLINE_ERROR_MESSAGE
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.common.tools import is_sdk_defined_working_offline
from demisto_sdk.utils.utils import update_command_args_from_config_file


def validate_version(value: Optional[str]) -> Optional[str]:
    """Validate that the version is in the format x.y.z where x, y, z are digits."""
    if value is None:
        return None  # Allow None values
    version_sections = value.split(".")
    if len(version_sections) == 3 and all(
        section.isdigit() for section in version_sections
    ):
        return value
    else:
        typer.echo(
            f"Version {value} is not in the expected format. The format should be x.y.z, e.g., 2.1.3.",
            err=True,
        )
    raise typer.Exit(1)


@logging_setup_decorator
def update_release_notes(
    ctx: typer.Context,
    input: str = typer.Option(
        None,
        "-i",
        "--input",
        help="The relative path of the content pack. For example Packs/Pack_Name",
    ),
    update_type: str = typer.Option(
        None,
        "-u",
        "--update-type",
        help="The type of update being done. [major, minor, revision, documentation]",
        metavar="UPDATE_TYPE",
    ),
    version: str = typer.Option(
        None,
        "-v",
        "--version",
        help="Bump to a specific version.",
        callback=validate_version,
    ),
    use_git: bool = typer.Option(
        False,
        "-g",
        "--use-git",
        help="Use git to identify the relevant changed files, will be used by default if '-i' is not set.",
    ),
    force: bool = typer.Option(
        False,
        "-f",
        "--force",
        help="Force update release notes for a pack (even if not required).",
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
        False,
        "-bc",
        "--breaking-changes",
        help="If new version contains breaking changes.",
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
        raise typer.Exit(1)

    update_command_args_from_config_file("update-release-notes", locals())

    if force and input is None:
        typer.echo(
            "<red>Please add a specific pack in order to force a release notes update.</red>"
        )
        raise typer.Exit(0)

    if not use_git and input is None:
        if not typer.confirm(
            "No specific pack was given, do you want to update all changed packs?"
        ):
            raise typer.Exit(0)

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
    raise typer.Exit(0)
