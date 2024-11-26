from pathlib import Path

import typer

from demisto_sdk.commands.common.constants import SDK_OFFLINE_ERROR_MESSAGE
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.common.tools import is_sdk_defined_working_offline
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.utils.utils import update_command_args_from_config_file


@logging_setup_decorator
def format(
    ctx: typer.Context,
    input: str = typer.Option(
        None,
        "-i",
        "--input",
        resolve_path=True,
        exists=True,
        help="The path of the script yml file or a comma-separated list. If not specified, the format will run "
        "on all new/changed files.",
    ),
    output: str = typer.Option(
        None,
        "-o",
        "--output",
        help="The path where the formatted file will be saved to.",
        resolve_path=True,
    ),
    from_version: str = typer.Option(
        None, "-fv", "--from-version", help="Specify fromversion of the pack."
    ),
    no_validate: bool = typer.Option(
        False, "-nv", "--no-validate", help="Set to skip validation on file."
    ),
    update_docker: bool = typer.Option(
        False,
        "-ud",
        "--update-docker",
        help="Set to update the docker image of the integration/script.",
    ),
    assume_yes: bool = typer.Option(
        None,
        "-y/-n",
        "--assume-yes/--assume-no",
        help="Automatically assume 'yes'/'no' to prompts and run non-interactively.",
    ),
    deprecate: bool = typer.Option(
        False,
        "-d",
        "--deprecate",
        help="Set to deprecate the integration/script/playbook.",
    ),
    use_git: bool = typer.Option(
        False,
        "-g",
        "--use-git",
        help="Use git to automatically recognize which files changed and run format on them.",
    ),
    prev_ver: str = typer.Option(
        None, "--prev-ver", help="Previous branch or SHA1 commit to run checks against."
    ),
    include_untracked: bool = typer.Option(
        False,
        "-iu",
        "--include-untracked",
        help="Whether to include untracked files in the formatting.",
    ),
    add_tests: bool = typer.Option(
        False,
        "-at",
        "--add-tests",
        help="Answer manually to add tests configuration prompt when running interactively.",
    ),
    id_set_path: Path = typer.Option(
        None,
        "-s",
        "--id-set-path",
        help="Deprecated. The path of the id_set json file.",
        exists=True,
        resolve_path=True,
    ),
    graph: bool = typer.Option(
        True,
        "-gr/-ngr",
        "--graph/--no-graph",
        help="Whether to use the content graph or not.",
    ),
    file_paths: list[Path] = typer.Argument(
        None, help="Paths of files to format.", exists=True, resolve_path=True
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
    """
    This command formats new or modified files to align with the Cortex standard.
    This is useful when developing a new integration, script, playbook, incident field, incident type, indicator field, indicator type, layout, or dashboard.
    When formatting is complete, the `validate` command runs and notifies you of any issues the formatter could not fix.

    """
    if is_sdk_defined_working_offline():
        typer.echo(SDK_OFFLINE_ERROR_MESSAGE, err=True)
        raise typer.Exit(1)

    update_command_args_from_config_file("format", ctx.params)
    _input = input if input else ",".join(map(str, file_paths)) if file_paths else None

    with ReadMeValidator.start_mdx_server():
        return format_manager(
            str(_input) if _input else None,
            str(output) if output else None,
            from_version=from_version,
            no_validate=no_validate,
            update_docker=update_docker,
            assume_answer=assume_yes,
            deprecate=deprecate,
            use_git=use_git,
            prev_ver=prev_ver,
            include_untracked=include_untracked,
            add_tests=add_tests,
            id_set_path=str(id_set_path) if id_set_path else None,
            use_graph=graph,
        )
