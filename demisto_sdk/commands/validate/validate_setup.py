import os
import sys
from pathlib import Path
from typing import List, Optional

import git
import typer

from demisto_sdk.commands.common.configuration import sdk
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


@logging_setup_decorator
def validate(
    ctx: typer.Context,
    config: dict,
    file_paths: List[Path] = typer.Argument([], help="File paths to validate"),
    no_conf_json: bool = typer.Option(
        False, "--no-conf-json", help="Skip conf.json validation."
    ),
    id_set: bool = typer.Option(
        False, "-s", "--id-set", help="Perform validations using the id_set file."
    ),
    id_set_path: Optional[Path] = typer.Option(
        None,
        "-idp",
        "--id-set-path",
        help="Path of the id-set.json used for validations.",
    ),
    graph: bool = typer.Option(
        False, "-gr", "--graph", help="Perform validations on content graph."
    ),
    prev_ver: Optional[str] = typer.Option(
        None, "--prev-ver", help="Previous branch or commit to run checks against."
    ),
    no_backward_comp: bool = typer.Option(
        False, "--no-backward-comp", help="Whether to check backward compatibility."
    ),
    use_git: bool = typer.Option(
        False, "-g", "--use-git", help="Validate changes using git."
    ),
    post_commit: bool = typer.Option(
        False, "-pc", "--post-commit", help="Run validation only on committed files."
    ),
    staged: bool = typer.Option(
        False, "-st", "--staged", help="Whether to ignore unstaged files."
    ),
    include_untracked: bool = typer.Option(
        False,
        "-iu",
        "--include-untracked",
        help="Whether to include untracked files in validation.",
    ),
    validate_all: bool = typer.Option(
        False, "-a", "--validate-all", help="Run all validation on all files."
    ),
    input: Optional[str] = typer.Option(
        None, "-i", "--input", help="Specific file or content pack to validate."
    ),
    skip_pack_release_notes: bool = typer.Option(
        False,
        "--skip-pack-release-notes",
        help="Skip validation of pack release notes.",
    ),
    print_ignored_errors: bool = typer.Option(
        False, "--print-ignored-errors", help="Print ignored errors as warnings."
    ),
    print_ignored_files: bool = typer.Option(
        False, "--print-ignored-files", help="Print which files were ignored."
    ),
    no_docker_checks: bool = typer.Option(
        False, "--no-docker-checks", help="Whether to run docker image validation."
    ),
    silence_init_prints: bool = typer.Option(
        False, "--silence-init-prints", help="Whether to skip initialization prints."
    ),
    skip_pack_dependencies: bool = typer.Option(
        False, "--skip-pack-dependencies", help="Skip validation of pack dependencies."
    ),
    create_id_set: bool = typer.Option(
        False, "--create-id-set", help="Whether to create the id_set.json file."
    ),
    json_file: Optional[str] = typer.Option(
        None, "-j", "--json-file", help="Path to the JSON file to output results."
    ),
    skip_schema_check: bool = typer.Option(
        False, "--skip-schema-check", help="Skip the file schema check."
    ),
    debug_git: bool = typer.Option(
        False, "--debug-git", help="Print debug logs for git statuses."
    ),
    print_pykwalify: bool = typer.Option(
        False, "--print-pykwalify", help="Print pykwalify log errors."
    ),
    quiet_bc_validation: bool = typer.Option(
        False,
        "--quiet-bc-validation",
        help="Set backward compatibility validation errors as warnings.",
    ),
    allow_skipped: bool = typer.Option(
        False, "--allow-skipped", help="Don't fail on skipped integrations."
    ),
    no_multiprocessing: bool = typer.Option(
        False, "--no-multiprocessing", help="Run validation without multiprocessing."
    ),
    run_specific_validations: Optional[str] = typer.Option(
        None,
        "-sv",
        "--run-specific-validations",
        help="Comma separated list of validations to run.",
    ),
    category_to_run: Optional[str] = typer.Option(
        None,
        "--category-to-run",
        help="Run validations by category in the config file.",
    ),
    fix: bool = typer.Option(
        False, "-f", "--fix", help="Auto-fix failing validations."
    ),
    config_path: Optional[Path] = typer.Option(
        None, "--config-path", help="Path for a config file to run."
    ),
    ignore_support_level: bool = typer.Option(
        False, "--ignore-support-level", help="Skip validations based on support level."
    ),
    run_old_validate: bool = typer.Option(
        False, "--run-old-validate", help="Run the old validate flow."
    ),
    skip_new_validate: bool = typer.Option(
        False, "--skip-new-validate", help="Skip the new validate flow."
    ),
    ignore: Optional[List[str]] = typer.Option(
        [], "--ignore", help="List of error codes to ignore."
    ),
):
    """Validate your content files. If no additional flags are given, will validate only committed files."""

    if is_sdk_defined_working_offline():
        logger.error(SDK_OFFLINE_ERROR_MESSAGE)
        sys.exit(1)

    # Use file_paths as input if not explicitly passed
    if not input and file_paths:
        input = ",".join(str(fp) for fp in file_paths)

    run_with_mp = not no_multiprocessing
    update_command_args_from_config_file("validate", locals())
    sys.path.append(sdk.configuration.env_dir)

    file_path = input

    if post_commit and staged:
        logger.info("<red>Cannot supply both staged and post-commit flags.</red>")
        sys.exit(1)

    try:
        is_external_repo = is_external_repository()
        if validate_all:  # validate_all is a Typer parameter
            execution_mode = ExecutionMode.ALL_FILES
        elif use_git:  # use_git is a Typer parameter
            execution_mode = ExecutionMode.USE_GIT
        elif file_path:
            execution_mode = ExecutionMode.SPECIFIC_FILES
        else:
            execution_mode = ExecutionMode.USE_GIT
            # default validate to -g --post-commit
            use_git = True
            post_commit = True

        exit_code = 0
        run_new_validate = (
            not skip_new_validate
            or str(os.getenv("SKIP_NEW_VALIDATE")).lower() == "true"
        )
        run_old_validate = (
            run_old_validate or str(os.getenv("RUN_OLD_VALIDATE")).lower() == "true"
        )

        if not run_new_validate:
            for flag in [
                "fix",
                "ignore_support_level",
                "config_path",
                "category_to_run",
            ]:
                if locals().get(flag):
                    logger.warning(
                        f"{flag.replace('_', '-')} is for the new validate flow, but not running it."
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
                if locals().get(flag):
                    logger.warning(
                        f"{flag.replace('_', '-')} is for the old validate flow, but not running it."
                    )

        if run_old_validate:
            validator = OldValidateManager(
                is_backward_check=not no_backward_comp,
                only_committed_files=post_commit,
                prev_ver=prev_ver,
                skip_conf_json=no_conf_json,
                use_git=use_git,
                file_path=file_path,
                validate_all=validate_all,
                validate_id_set=id_set,
                validate_graph=graph,
                skip_pack_rn_validation=skip_pack_release_notes,
                print_ignored_errors=print_ignored_errors,
                is_external_repo=is_external_repo,
                print_ignored_files=print_ignored_files,
                no_docker_checks=no_docker_checks,
                silence_init_prints=silence_init_prints,
                skip_dependencies=skip_pack_dependencies,
                id_set_path=id_set_path,
                staged=staged,
                create_id_set=create_id_set,
                json_file_path=json_file,
                skip_schema_check=skip_schema_check,
                debug_git=debug_git,
                include_untracked=include_untracked,
                quiet_bc=quiet_bc_validation,
                multiprocessing=run_with_mp,
                check_is_unskipped=not allow_skipped,
                specific_validations=run_specific_validations.split(",")
                if run_specific_validations
                else [],
            )
            exit_code += validator.run_validation()

        if run_new_validate:
            validation_results = ResultWriter(json_file_path=json_file)
            config_reader = ConfigReader(
                path=config_path,
                category=category_to_run,
                explicitly_selected=run_specific_validations.split(",")
                if run_specific_validations
                else [],
            )
            initializer = Initializer(
                staged=staged,
                committed_only=post_commit,
                prev_ver=prev_ver,
                file_path=file_path,
                execution_mode=execution_mode,
            )
            validator_v2 = ValidateManager(
                file_path=file_path,
                initializer=initializer,
                validation_results=validation_results,
                config_reader=config_reader,
                allow_autofix=fix,
                ignore_support_level=ignore_support_level,
                ignore=ignore,
            )
            exit_code += validator_v2.run_validations()

        return exit_code

    except (git.InvalidGitRepositoryError, git.NoSuchPathError, FileNotFoundError) as e:
        logger.error(f"{e}")
        logger.error(
            "\nYou may not be running `demisto-sdk validate` command in the content directory.\n Please run the command from content directory"
        )

        sys.exit(1)
