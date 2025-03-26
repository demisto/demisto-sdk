from pathlib import Path
from typing import Optional

import typer

from demisto_sdk.commands.common.logger import logging_setup


def pre_commit(
    ctx: typer.Context,
    input_files: Optional[list[Path]] = typer.Option(
        None,
        "-i",
        "--input",
        "--files",
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help="The paths to run pre-commit on. May pass multiple paths.",
    ),
    staged_only: bool = typer.Option(
        False, "--staged-only", help="Whether to run only on staged files."
    ),
    commited_only: bool = typer.Option(
        False, "--commited-only", help="Whether to run on committed files only."
    ),
    git_diff: bool = typer.Option(
        False,
        "--git-diff",
        "-g",
        help="Whether to use git to determine which files to run on.",
    ),
    prev_version: Optional[str] = typer.Option(
        None,
        "--prev-version",
        help="The previous version to compare against. "
        "If not provided, the previous version will be determined using git.",
    ),
    all_files: bool = typer.Option(
        False, "--all-files", "-a", help="Whether to run on all files."
    ),
    mode: str = typer.Option(
        "", "--mode", help="Special mode to run the pre-commit with."
    ),
    skip: Optional[list[str]] = typer.Option(
        None, "--skip", help="A list of precommit hooks to skip."
    ),
    validate: bool = typer.Option(
        True,
        "--validate/--no-validate",
        help="Whether to run demisto-sdk validate or not.",
    ),
    format: bool = typer.Option(
        False, "--format/--no-format", help="Whether to run demisto-sdk format or not."
    ),
    secrets: bool = typer.Option(
        True,
        "--secrets/--no-secrets",
        help="Whether to run demisto-sdk secrets or not.",
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Verbose output of pre-commit."
    ),
    show_diff_on_failure: bool = typer.Option(
        False, "--show-diff-on-failure", help="Show diff on failure."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Whether to run the pre-commit hooks in dry-run mode, which will only create the config file.",
    ),
    docker: bool = typer.Option(
        True, "--docker/--no-docker", help="Whether to run docker based hooks or not."
    ),
    image_ref: Optional[str] = typer.Option(
        None,
        "--image-ref",
        help="The docker image reference to run docker hooks with. Overrides the docker image from YAML "
        "or native image config.",
    ),
    docker_image: Optional[str] = typer.Option(
        None,
        "--docker-image",
        help="Override the `docker_image` property in the template file. This is a comma separated "
        "list of: `from-yml`, `native:dev`, `native:ga`, `native:candidate`.",
    ),
    run_hook: Optional[str] = typer.Argument(None, help="A specific hook to run"),
    pre_commit_template_path: Optional[Path] = typer.Option(
        None,
        "--template-path",
        envvar="PRE_COMMIT_TEMPLATE_PATH",
        help="A custom path for pre-defined pre-commit template, if not provided will use the default template.",
    ),
    console_log_threshold: str = typer.Option(
        "INFO",
        "-clt",
        "--console-log-threshold",
        help="Minimum logging threshold for the console logger.",
    ),
    file_log_threshold: str = typer.Option(
        "DEBUG",
        "-flt",
        "--file-log-threshold",
        help="Minimum logging threshold for the file logger.",
    ),
    log_file_path: Optional[str] = typer.Option(
        None,
        "-lp",
        "--log-file-path",
        help="Path to save log files onto.",
    ),
):
    """
    This command enhances the content development experience, by running a variety of checks and linters.
    It utilizes the [pre-commit](https://github.com/pre-commit/pre-commit) framework.
    A `.pre-commit-config-template.yaml` file is used to configure the hooks (if found in the content repo.
    Otherwise, a [default](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/pre_commit/.pre-commit-config_template.yaml) is used)

    Since content items are made to run in containers with different Python versions and dependencies,
    this command matches content items with suitable configurations, before passing the generated (temporary) `.pre-commit-config.yaml` file.

    **Note**: An internet connection is required for this command.
    """
    logging_setup(
        console_threshold=console_log_threshold,
        file_threshold=file_log_threshold,
        path=log_file_path,
        calling_function="pre-commit",
    )

    from demisto_sdk.commands.pre_commit.pre_commit_command import pre_commit_manager

    return_code = pre_commit_manager(
        input_files,
        staged_only,
        commited_only,
        git_diff,
        prev_version,
        all_files,
        mode,
        skip,
        validate,
        format,
        secrets,
        verbose,
        show_diff_on_failure,
        run_docker_hooks=docker,
        image_ref=image_ref,
        docker_image=docker_image,
        dry_run=dry_run,
        run_hook=run_hook,
        pre_commit_template_path=pre_commit_template_path,
    )
    if return_code:
        raise typer.Exit(1)
