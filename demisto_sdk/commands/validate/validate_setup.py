import os
import sys
import git
from pathlib import Path

import typer

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.common.tools import is_sdk_defined_working_offline, is_external_repository
from demisto_sdk.commands.validate.config_reader import ConfigReader
from demisto_sdk.commands.validate.initializer import Initializer
from demisto_sdk.commands.validate.validation_results import ResultWriter
from demisto_sdk.utils.utils import update_command_args_from_config_file


@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
def validate(
        ctx: typer.Context,
        config: ConfigType,
        file_paths: list[Path] = typer.Argument(..., exists=True, resolve_path=True),
        no_conf_json: bool = typer.Option(False, help="Skip conf.json validation."),
        id_set: bool = typer.Option(False, help="Perform validations using the id_set file."),
        id_set_path: Path = typer.Option(None, help="Path of the id-set.json used for validations."),
        graph: bool = typer.Option(False, help="Perform validations on content graph."),
        prev_ver: str = typer.Option(None, help="Previous branch or SHA1 commit to run checks against."),
        no_backward_comp: bool = typer.Option(False, help="Whether to check backward compatibility."),
        use_git: bool = typer.Option(False, help="Validate changes using git."),
        post_commit: bool = typer.Option(False, help="Run validation only on committed changed files."),
        staged: bool = typer.Option(False, help="Ignore unstaged files."),
        include_untracked: bool = typer.Option(False, help="Whether to include untracked files in the validation."),
        validate_all: bool = typer.Option(False, help="Run all validation on all files."),
        input: list[Path] = typer.Option(None, help="Path of the content pack/file to validate."),
        skip_pack_release_notes: bool = typer.Option(False, help="Skip validation of pack release notes."),
        print_ignored_errors: bool = typer.Option(False, help="Print ignored errors as warnings."),
        print_ignored_files: bool = typer.Option(False, help="Print ignored files."),
        no_docker_checks: bool = typer.Option(False, help="Whether to run docker image validation."),
        silence_init_prints: bool = typer.Option(False, help="Skip the initialization prints."),
        skip_pack_dependencies: bool = typer.Option(False, help="Skip validation of pack dependencies."),
        create_id_set: bool = typer.Option(False, help="Whether to create the id_set.json file."),
        json_file: Path = typer.Option(None, help="The JSON file path to output command results."),
        skip_schema_check: bool = typer.Option(False, help="Whether to skip the file schema check."),
        debug_git: bool = typer.Option(False, help="Whether to print debug logs for git statuses."),
        print_pykwalify: bool = typer.Option(False, help="Whether to print the pykwalify log errors."),
        quiet_bc_validation: bool = typer.Option(False,
                                                 help="Set backward compatibility validation errors as warnings."),
        allow_skipped: bool = typer.Option(False, help="Don't fail on skipped integrations."),
        no_multiprocessing: bool = typer.Option(False, help="Run validate all without multiprocessing."),
        run_specific_validations: str = typer.Option(None, help="Comma separated list of validations to run."),
        category_to_run: str = typer.Option(None, help="Run specific validations by stating category."),
        fix: bool = typer.Option(False, help="Whether to autofix failing validations."),
        config_path: str = typer.Option(None, help="Path for a config file to run."),
        ignore_support_level: bool = typer.Option(False, help="Skip validations based on support level."),
        run_old_validate: bool = typer.Option(False, help="Whether to run the old validate flow."),
        skip_new_validate: bool = typer.Option(False, help="Whether to skip the new validate flow."),
        ignore: list[str] = typer.Option(None, help="An error code to not run. Can be repeated.")
):
    """Validate your content files. If no additional flags are given, will validate only committed files."""
    from demisto_sdk.commands.validate.old_validate_manager import OldValidateManager
    from demisto_sdk.commands.validate.validate_manager import ValidateManager

    if is_sdk_defined_working_offline():
        typer.echo("SDK is offline. Exiting.", err=True)
        sys.exit(1)

    if file_paths and not input:
        input = [str(fp) for fp in file_paths]

    run_with_mp = not no_multiprocessing
    update_command_args_from_config_file("validate", locals())
    sys.path.append(config.configuration.env_dir)

    file_path = input

    if post_commit and staged:
        typer.echo("Could not supply the staged flag with the post-commit flag", err=True)
        sys.exit(1)

    try:
        is_external_repo = is_external_repository()
        if validate_all:
            execution_mode = ExecutionMode.ALL_FILES
        elif use_git:
            execution_mode = ExecutionMode.USE_GIT
        elif file_path:
            execution_mode = ExecutionMode.SPECIFIC_FILES
        else:
            execution_mode = ExecutionMode.USE_GIT
            # default validate to -g --post-commit
            use_git = True
            post_commit = True

        exit_code = 0
        run_new_validate = not skip_new_validate or (
                (env_flag := os.getenv("SKIP_NEW_VALIDATE"))
                and str(env_flag).lower() == "true"
        )
        run_old_validate = run_old_validate or (
                (env_flag := os.getenv("RUN_OLD_VALIDATE"))
                and str(env_flag).lower() == "true"
        )

        if not run_new_validate:
            for new_validate_flag in [
                "fix",
                "ignore_support_level",
                "config_path",
                "category_to_run",
            ]:
                if locals().get(new_validate_flag):
                    typer.echo(
                        f"The following flag {new_validate_flag.replace('_', '-')} is related only to the new validate "
                        f"and is being called while not running the new validate flow, "
                        f"therefore the flag will be ignored.",
                        err=True
                    )

        if not run_old_validate:
            for old_validate_flag in [
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
                if locals().get(old_validate_flag):
                    typer.echo(
                        f"The following flag {old_validate_flag.replace('_', '-')} is related only to the old validate "
                        f"and is being called while not running the old validate flow, "
                        f"therefore the flag will be ignored.",
                        err=True
                    )

        if run_old_validate:
            if not skip_new_validate:
                graph = False
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
                specific_validations=run_specific_validations,
            )
            exit_code += validator.run_validation()

        if run_new_validate:
            validation_results = ResultWriter(
                json_file_path=json_file,
            )
            config_reader = ConfigReader(
                path=config_path,
                category=category_to_run,
                explicitly_selected=(run_specific_validations or "").split(","),
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
        typer.echo(f"{e}", err=True)
        typer.echo(
            "\nYou may not be running `demisto-sdk validate` command in the content directory.\n"
            "Please run the command from content directory", err=True
        )
        sys.exit(1)
