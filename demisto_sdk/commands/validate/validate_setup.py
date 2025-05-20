import os
import sys
from pathlib import Path
from typing import Optional

import git
import typer

from demisto_sdk.commands.common.constants import (
    SDK_OFFLINE_ERROR_MESSAGE,
    ExecutionMode,
)
from demisto_sdk.commands.common.logger import logger, logging_setup_decorator
from demisto_sdk.commands.common.tools import (
    is_external_repository,
    is_sdk_defined_working_offline,
)
from demisto_sdk.commands.validate.config_reader import ConfigReader
from demisto_sdk.commands.validate.initializer import Initializer
from demisto_sdk.commands.validate.old_validate_manager import OldValidateManager
from demisto_sdk.commands.validate.validate_manager import ValidateManager
from demisto_sdk.commands.validate.validation_results import ResultWriter
from demisto_sdk.utils.utils import update_command_args_from_config_file


def validate_paths(value: Optional[str]) -> Optional[str]:
    if not value:  # If no input is provided, just return None
        return None

    paths = value.split(",")
    for path in paths:
        stripped_path = path.strip()
        if not os.path.exists(stripped_path):  # noqa: PTH110
            raise typer.BadParameter(f"The path '{stripped_path}' does not exist.")

    return value


@logging_setup_decorator
def validate(
    ctx: typer.Context,
    file_paths: str = typer.Argument(None, exists=True, resolve_path=True),
    no_conf_json: bool = typer.Option(False, help="Skip conf.json validation."),
    id_set: bool = typer.Option(
        False, "-s", "--id-set", help="Perform validations using the id_set file."
    ),
    id_set_path: Path = typer.Option(
        None,
        "-idp",
        "--id-set-path",
        help="Path of the id-set.json used for validations.",
    ),
    graph: bool = typer.Option(
        False, "-gr", "--graph", help="Perform validations on content graph."
    ),
    prev_ver: str = typer.Option(
        None, help="Previous branch or SHA1 commit to run checks against."
    ),
    no_backward_comp: bool = typer.Option(
        False, help="Whether to check backward compatibility."
    ),
    use_git: bool = typer.Option(
        False, "-g", "--use-git", help="Validate changes using git."
    ),
    post_commit: bool = typer.Option(
        False,
        "-pc",
        "--post-commit",
        help="Run validation only on committed changed files.",
    ),
    staged: bool = typer.Option(
        False, "-st", "--staged", help="Ignore unstaged files."
    ),
    include_untracked: bool = typer.Option(
        False,
        "-iu",
        "--include-untracked",
        help="Whether to include untracked files in the validation.",
    ),
    validate_all: bool = typer.Option(
        False, "-a", "--validate-all", help="Run all validation on all files."
    ),
    input: Optional[str] = typer.Option(
        None,
        "-i",
        "--input",
        help="Path of the content pack/file to validate.",
        callback=validate_paths,
    ),
    skip_pack_release_notes: bool = typer.Option(
        False, help="Skip validation of pack release notes."
    ),
    print_ignored_errors: bool = typer.Option(
        False, help="Print ignored errors as warnings."
    ),
    print_ignored_files: bool = typer.Option(False, help="Print ignored files."),
    no_docker_checks: bool = typer.Option(
        False, help="Whether to run docker image validation."
    ),
    silence_init_prints: bool = typer.Option(
        False, help="Skip the initialization prints."
    ),
    skip_pack_dependencies: bool = typer.Option(
        False, help="Skip validation of pack dependencies."
    ),
    create_id_set: bool = typer.Option(
        False, help="Whether to create the id_set.json file."
    ),
    json_file: str = typer.Option(
        None, "-j", "--json-file", help="The JSON file path to output command results."
    ),
    skip_schema_check: bool = typer.Option(
        False, help="Whether to skip the file schema check."
    ),
    debug_git: bool = typer.Option(
        False, help="Whether to print debug logs for git statuses."
    ),
    print_pykwalify: bool = typer.Option(
        False, help="Whether to print the pykwalify log errors."
    ),
    quiet_bc_validation: bool = typer.Option(
        False, help="Set backward compatibility validation errors as warnings."
    ),
    allow_skipped: bool = typer.Option(
        False, help="Don't fail on skipped integrations."
    ),
    no_multiprocessing: bool = typer.Option(
        False, help="Run validate all without multiprocessing."
    ),
    run_specific_validations: str = typer.Option(
        None,
        "-sv",
        "--run-specific-validations",
        help="Comma separated list of validations to run.",
    ),
    allow_ignore_all_errors: bool = typer.Option(
        False,
        "-iae",
        "--allow-ignore-all-errors",
        help="Whether to allow ignoring all error_codes or only the ones appear in the config file.",
    ),
    category_to_run: str = typer.Option(
        None, help="Run specific validations by stating category."
    ),
    fix: bool = typer.Option(
        False, "-f", "--fix", help="Whether to autofix failing validations."
    ),
    config_path: Path = typer.Option(None, help="Path for a config file to run."),
    ignore_support_level: bool = typer.Option(
        False, help="Skip validations based on support level."
    ),
    run_old_validate: bool = typer.Option(
        False, help="Whether to run the old validate flow."
    ),
    skip_new_validate: bool = typer.Option(
        False, help="Whether to skip the new validate flow."
    ),
    ignore: list[str] = typer.Option(
        None, help="An error code to not run. Can be repeated."
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
    This command ensures that the content repository files are valid and are able to be processed by the platform.
    This is used in our validation process both locally and in Gitlab.
    """
    if is_sdk_defined_working_offline():
        typer.echo(SDK_OFFLINE_ERROR_MESSAGE, err=True)
        raise typer.Exit(1)

    if file_paths and not input:
        input = file_paths

    run_with_mp = not no_multiprocessing
    update_command_args_from_config_file("validate", ctx.params)
    sdk = ctx.obj
    sys.path.append(sdk.configuration.env_dir)

    if post_commit and staged:
        logger.error("Cannot use both post-commit and staged flags.")
        raise typer.Exit(1)

    is_external_repo = is_external_repository()
    file_path = input
    execution_mode = determine_execution_mode(
        file_path, validate_all, use_git, post_commit
    )
    exit_code = 0

    # Check environment variables
    run_new_validate = not skip_new_validate or (
        (env_flag := os.getenv("SKIP_NEW_VALIDATE")) and str(env_flag).lower() == "true"
    )
    run_old_validate = run_old_validate or (
        (env_flag := os.getenv("RUN_OLD_VALIDATE")) and str(env_flag).lower() == "true"
    )

    # Log warnings for ignored flags
    warn_on_ignored_flags(run_new_validate, run_old_validate, ctx.params)

    try:
        # Run old validation flow
        if run_old_validate:
            logger.warning(
                "<yellow>Old validate is being used. This flow will be deprecated and removed in the near future. Please use the new validate flow.</yellow>"
            )
            exit_code += run_old_validation(
                file_path, is_external_repo, run_with_mp, **ctx.params
            )

        # Run new validation flow
        if run_new_validate:
            exit_code += run_new_validation(file_path, execution_mode, **ctx.params)

        raise typer.Exit(code=exit_code)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError, FileNotFoundError) as e:
        logger.error(f"{e}")
        logger.error(
            "You may not be running `demisto-sdk validate` from the content directory.\n"
            "Please run this command from the content directory."
        )
        raise typer.Exit(1)


def determine_execution_mode(file_path, validate_all, use_git, post_commit):
    if validate_all:
        return ExecutionMode.ALL_FILES
    elif file_path:
        return ExecutionMode.SPECIFIC_FILES
    elif use_git:
        return ExecutionMode.USE_GIT
    else:
        # Default case: fall back to using git for validation
        return ExecutionMode.USE_GIT


def warn_on_ignored_flags(run_new_validate, run_old_validate, params):
    if not run_new_validate:
        for flag in ["fix", "ignore_support_level", "config_path", "category_to_run"]:
            if params.get(flag):
                logger.warning(
                    f"Flag '{flag.replace('_', '-')}' is ignored when skipping new validation."
                )

    if not run_old_validate:
        for flag in [
            "no_backward_comp",
            "no_conf_json",
            "id_set",
            "graph",
            "skip_pack_release_notes",
            "print_ignored_errors",
            "print_ignored_files",
            "no_docker_checks",
            "silence_init_prints",
            "skip_pack_dependencies",
            "id_set_path",
            "create_id_set",
            "skip_schema_check",
            "debug_git",
            "include_untracked",
            "quiet_bc_validation",
            "allow_skipped",
            "no_multiprocessing",
        ]:
            if params.get(flag):
                logger.warning(
                    f"Flag '{flag.replace('_', '-')}' is ignored when skipping old validation."
                )


def run_old_validation(file_path, is_external_repo, run_with_mp, **kwargs):
    validator = OldValidateManager(
        is_backward_check=not kwargs["no_backward_comp"],
        only_committed_files=kwargs["post_commit"],
        prev_ver=kwargs["prev_ver"],
        skip_conf_json=kwargs["no_conf_json"],
        use_git=kwargs["use_git"],
        file_path=file_path,
        validate_all=kwargs["validate_all"],
        validate_id_set=kwargs["id_set"],
        validate_graph=kwargs["graph"],
        skip_pack_rn_validation=kwargs["skip_pack_release_notes"],
        print_ignored_errors=kwargs["print_ignored_errors"],
        is_external_repo=is_external_repo,
        print_ignored_files=kwargs["print_ignored_files"],
        no_docker_checks=kwargs["no_docker_checks"],
        silence_init_prints=kwargs["silence_init_prints"],
        skip_dependencies=kwargs["skip_pack_dependencies"],
        id_set_path=kwargs["id_set_path"],
        staged=kwargs["staged"],
        create_id_set=kwargs["create_id_set"],
        json_file_path=kwargs["json_file"],
        skip_schema_check=kwargs["skip_schema_check"],
        debug_git=kwargs["debug_git"],
        include_untracked=kwargs["include_untracked"],
        quiet_bc=kwargs["quiet_bc_validation"],
        multiprocessing=run_with_mp,
        check_is_unskipped=not kwargs.get("allow_skipped", False),
        specific_validations=kwargs.get("run_specific_validations"),
    )
    return validator.run_validation()


def run_new_validation(file_path, execution_mode, **kwargs):
    validation_results = ResultWriter(json_file_path=kwargs.get("json_file"))
    config_reader = ConfigReader(
        path=kwargs.get("config_path"),
        category=kwargs.get("category_to_run"),
        explicitly_selected=(kwargs.get("run_specific_validations") or "").split(","),
        allow_ignore_all_errors=kwargs["allow_ignore_all_errors"],
    )
    initializer = Initializer(
        staged=kwargs["staged"],
        committed_only=kwargs["post_commit"],
        prev_ver=kwargs["prev_ver"],
        file_path=file_path,
        execution_mode=execution_mode,
    )
    validator_v2 = ValidateManager(
        file_path=file_path,
        initializer=initializer,
        validation_results=validation_results,
        config_reader=config_reader,
        allow_autofix=kwargs["fix"],
        ignore_support_level=kwargs["ignore_support_level"],
        ignore=kwargs["ignore"],
    )
    return validator_v2.run_validations()
