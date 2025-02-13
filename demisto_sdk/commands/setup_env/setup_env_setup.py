from pathlib import Path
from typing import Tuple

import typer

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.setup_env.setup_environment import IDEType, setup_env


@logging_setup_decorator
def setup_env_command(
    ctx: typer.Context,
    ide: str = typer.Option(
        "auto-detect",
        "--ide",
        help="IDE type to configure the environment for. If not specified, "
        "the IDE will be auto-detected. Case-insensitive.",
    ),
    input: list[Path] = typer.Option(
        None,
        "-i",
        "--input",
        help="Paths to content integrations or script to setup the environment. If not provided, "
        "will configure the environment for the content repository.",
    ),
    create_virtualenv: bool = typer.Option(
        False, "--create-virtualenv", help="Create a virtualenv for the environment."
    ),
    overwrite_virtualenv: bool = typer.Option(
        False,
        "--overwrite-virtualenv",
        help="Overwrite existing virtualenvs. Relevant only if the 'create-virtualenv' flag is used.",
    ),
    secret_id: str = typer.Option(
        None,
        "--secret-id",
        help="Secret ID to use for the Google Secret Manager instance. Requires the `DEMISTO_SDK_GCP_PROJECT_ID` "
        "environment variable to be set.",
    ),
    instance_name: str = typer.Option(
        None, "--instance-name", help="Instance name to configure in XSOAR / XSIAM."
    ),
    run_test_module: bool = typer.Option(
        False,
        "--run-test-module",
        help="Whether to run test-module on the configured XSOAR / XSIAM instance.",
    ),
    clean: bool = typer.Option(
        False,
        "--clean",
        help="Clean the repository of temporary files created by the 'lint' command.",
    ),
    file_paths: Tuple[Path, ...] = typer.Argument(
        None,
        resolve_path=True,
        show_default=False,
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
    The setup-env command creates a content environment and integration/script environment.
    The command will configure VSCode and XSOAR/XSIAM instances for development and testing.
    """
    if ide.lower() == "auto-detect":
        if (CONTENT_PATH / ".vscode").exists():
            typer.echo(
                "Visual Studio Code IDEType has been detected and will be configured."
            )
            ide_type = IDEType.VSCODE
        elif (CONTENT_PATH / ".idea").exists():
            typer.echo(
                "PyCharm / IDEA IDEType has been detected and will be configured."
            )
            ide_type = IDEType.PYCHARM
        else:
            raise RuntimeError(
                "Could not detect IDEType. Please select a specific IDEType using the --ide flag."
            )
    else:
        ide_type = IDEType(ide)

    # Resolve input paths if provided
    resolved_file_paths = (
        tuple(Path(path).resolve() for path in input) if input else tuple()
    )

    # If no input key was found, try to resolve arg
    if not resolved_file_paths and file_paths:
        file_paths = tuple(Path(path).resolve() for path in file_paths)
        resolved_file_paths = file_paths

    setup_env(
        file_paths=resolved_file_paths,
        ide_type=ide_type,
        create_virtualenv=create_virtualenv,
        overwrite_virtualenv=overwrite_virtualenv,
        secret_id=secret_id,
        instance_name=instance_name,
        test_module=run_test_module,
        clean=clean,
    )
