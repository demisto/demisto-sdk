# Site packages
import platform
import sys

import click

from demisto_sdk.commands.validate.config_reader import ConfigReader
from demisto_sdk.commands.validate.initializer import Initializer
from demisto_sdk.commands.validate.validation_results import ResultWriter
from demisto_sdk.commands.xsoar_linter.xsoar_linter import xsoar_linter_manager

try:
    import git
except ImportError:
    sys.exit(click.style("Git executable cannot be found, or is invalid", fg="red"))

import copy
import functools
import logging
import os
from pathlib import Path
from typing import IO, Any, Dict, List, Optional, Tuple, Union

import typer
from pkg_resources import DistributionNotFound, get_distribution

from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    DEMISTO_SDK_MARKETPLACE_XSOAR_DIST_DEV,
    ENV_DEMISTO_SDK_MARKETPLACE,
    FileType,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content_constant_paths import (
    ALL_PACKS_DEPENDENCIES_DEFAULT_PATH,
    CONTENT_PATH,
)
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.logger import (
    handle_deprecated_args,
    logger,
    logging_setup,
)
from demisto_sdk.commands.common.tools import (
    find_type,
    get_last_remote_release_version,
    get_release_note_entries,
    is_external_repository,
    is_sdk_defined_working_offline,
    parse_marketplace_kwargs,
)
from demisto_sdk.commands.content_graph.commands.create import create
from demisto_sdk.commands.content_graph.commands.get_dependencies import (
    get_dependencies,
)
from demisto_sdk.commands.content_graph.commands.get_relationships import (
    get_relationships,
)
from demisto_sdk.commands.content_graph.commands.update import update
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.generate_modeling_rules import generate_modeling_rules
from demisto_sdk.commands.prepare_content.prepare_upload_manager import (
    PrepareUploadManager,
)
from demisto_sdk.commands.setup_env.setup_environment import IDEType
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter
from demisto_sdk.commands.test_content.test_modeling_rule import (
    init_test_data,
    test_modeling_rule,
)
from demisto_sdk.commands.upload.upload import upload_content_entity
from demisto_sdk.utils.utils import check_configuration_file

SDK_OFFLINE_ERROR_MESSAGE = (
    "[red]An internet connection is required for this command. If connected to the "
    "internet, un-set the DEMISTO_SDK_OFFLINE_ENV environment variable.[/red]"
)


# Third party packages

# Common tools


class PathsParamType(click.Path):
    """
    Defines a click options type for use with the @click.option decorator

    The type accepts a string of comma-separated values where each individual value adheres
    to the definition for the click.Path type. The class accepts the same parameters as the
    click.Path type, applying those arguments for each comma-separated value in the list.
    See https://click.palletsprojects.com/en/8.0.x/parameters/#implementing-custom-types for
    more details.
    """

    def convert(self, value, param, ctx):
        if "," not in value:
            return super().convert(value, param, ctx)

        split_paths = value.split(",")
        # check the validity of each of the paths
        _ = [
            super(PathsParamType, self).convert(path, param, ctx)
            for path in split_paths
        ]
        return value


class VersionParamType(click.ParamType):
    """
    Defines a click options type for use with the @click.option decorator

    The type accepts a string represents a version number.
    """

    name = "version"

    def convert(self, value, param, ctx):
        version_sections = value.split(".")
        if len(version_sections) == 3 and all(
            version_section.isdigit() for version_section in version_sections
        ):
            return value
        else:
            self.fail(
                f"Version {value} is not according to the expected format. "
                f"The format of version should be in x.y.z format, e.g: <2.1.3>",
                param,
                ctx,
            )


class DemistoSDK:
    """
    The core class for the SDK.
    """

    def __init__(self):
        self.configuration = None


pass_config = click.make_pass_decorator(DemistoSDK, ensure=True)


def logging_setup_decorator(func, *args, **kwargs):
    def get_context_arg(args):
        for arg in args:
            if type(arg) == click.core.Context:
                return arg
        print(  # noqa: T201
            "Error: Cannot find the Context arg. Is the command configured correctly?"
        )
        return None

    @click.option(
        "--console-log-threshold",
        help="Minimum logging threshold for the console logger."
        " Possible values: DEBUG, INFO, WARNING, ERROR.",
    )
    @click.option(
        "--file-log-threshold",
        help="Minimum logging threshold for the file logger."
        " Possible values: DEBUG, INFO, WARNING, ERROR.",
    )
    @click.option("--log-file-path", help="Path to save log files onto.")
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logging_setup(
            console_log_threshold=kwargs.get("console_log_threshold") or logging.INFO,
            file_log_threshold=kwargs.get("file_log_threshold") or logging.DEBUG,
            log_file_path=kwargs.get("log_file_path"),
        )

        handle_deprecated_args(get_context_arg(args).args)
        return func(*args, **kwargs)

    return wrapper


@click.group(
    invoke_without_command=True,
    no_args_is_help=True,
    context_settings=dict(max_content_width=100),
)
@click.help_option("-h", "--help")
@click.option(
    "-v",
    "--version",
    help="Get the demisto-sdk version.",
    is_flag=True,
    default=False,
    show_default=True,
)
@click.option(
    "-rn",
    "--release-notes",
    help="Get the release notes of the current demisto-sdk version.",
    is_flag=True,
    default=False,
    show_default=True,
)
@pass_config
@click.pass_context
def main(ctx, config, version, release_notes, **kwargs):
    logging_setup(
        console_log_threshold=kwargs.get("console_log_threshold", logging.INFO),
        file_log_threshold=kwargs.get("file_log_threshold", logging.DEBUG),
        log_file_path=kwargs.get("log_file_path"),
        skip_log_file_creation=True,  # Log file creation is handled in the logger setup of the sub-command
    )
    handle_deprecated_args(ctx.args)

    config.configuration = Configuration()
    import dotenv

    dotenv.load_dotenv(CONTENT_PATH / ".env", override=True)  # type: ignore # load .env file from the cwd

    if platform.system() == "Windows":
        logger.warning(
            "Using Demisto-SDK on Windows is not supported. Use WSL2 or run in a container."
        )

    if (
        (not os.getenv("DEMISTO_SDK_SKIP_VERSION_CHECK")) or version
    ) and not is_sdk_defined_working_offline():  # If the key exists/called to version
        try:
            __version__ = get_distribution("demisto-sdk").version
        except DistributionNotFound:
            __version__ = "dev"
            logger.info(
                "[yellow]Could not find the version of the demisto-sdk. This usually happens when running in a development environment.[/yellow]"
            )
        else:
            last_release = ""
            if not os.environ.get(
                "CI"
            ):  # Check only when not running in CI (e.g running locally).
                last_release = get_last_remote_release_version()
            logger.info(f"[yellow]You are using demisto-sdk {__version__}.[/yellow]")
            if last_release and __version__ != last_release:
                logger.warning(
                    f"A newer version ({last_release}) is available. "
                    f"To update, run 'pip3 install --upgrade demisto-sdk'"
                )
            if release_notes:
                rn_entries = get_release_note_entries(__version__)

                if not rn_entries:
                    logger.warning(
                        "\n[yellow]Could not get the release notes for this version.[/yellow]"
                    )
                else:
                    logger.info(
                        "\nThe following are the release note entries for the current version:\n"
                    )
                    for rn in rn_entries:
                        logger.info(rn)
                    logger.info("")


# ====================== split ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option("-i", "--input", help="The yml/json file to extract from", required=True)
@click.option(
    "-o",
    "--output",
    help="The output dir to write the extracted code/description/image/json to.",
)
@click.option(
    "--no-demisto-mock",
    help="Don't add an import for demisto mock. (only for yml files)",
    is_flag=True,
    show_default=True,
)
@click.option(
    "--no-common-server",
    help="Don't add an import for CommonServerPython. (only for yml files)",
    is_flag=True,
    show_default=True,
)
@click.option(
    "--no-auto-create-dir",
    help="Don't auto create the directory if the target directory ends with *Integrations/*Scripts/*Dashboards"
    "/*GenericModules.",
    is_flag=True,
    show_default=True,
)
@click.option(
    "--new-module-file",
    help="Create a new module file instead of editing the existing file. (only for json files)",
    is_flag=True,
    show_default=True,
)
@pass_config
@click.pass_context
@logging_setup_decorator
def split(ctx, config, **kwargs):
    """Split the code, image and description files from a Demisto integration or script yaml file
    to multiple files(To a package format - https://demisto.pan.dev/docs/package-dir).
    """
    from demisto_sdk.commands.split.jsonsplitter import JsonSplitter

    check_configuration_file("split", kwargs)
    file_type: FileType = find_type(kwargs.get("input", ""), ignore_sub_categories=True)
    if file_type not in [
        FileType.INTEGRATION,
        FileType.SCRIPT,
        FileType.GENERIC_MODULE,
        FileType.MODELING_RULE,
        FileType.PARSING_RULE,
        FileType.LISTS,
        FileType.ASSETS_MODELING_RULE,
    ]:
        logger.info(
            "[red]File is not an Integration, Script, List, Generic Module, Modeling Rule or Parsing Rule.[/red]"
        )
        return 1

    if file_type in [
        FileType.INTEGRATION,
        FileType.SCRIPT,
        FileType.MODELING_RULE,
        FileType.PARSING_RULE,
        FileType.ASSETS_MODELING_RULE,
    ]:
        yml_splitter = YmlSplitter(
            configuration=config.configuration, file_type=file_type.value, **kwargs
        )
        return yml_splitter.extract_to_package_format()

    else:
        json_splitter = JsonSplitter(
            input=kwargs.get("input"),  # type: ignore[arg-type]
            output=kwargs.get("output"),  # type: ignore[arg-type]
            no_auto_create_dir=kwargs.get("no_auto_create_dir"),  # type: ignore[arg-type]
            new_module_file=kwargs.get("new_module_file"),  # type: ignore[arg-type]
            file_type=file_type,
        )
        return json_splitter.split_json()


# ====================== extract-code ====================== #
@main.command(hidden=True)
@click.help_option("-h", "--help")
@click.option("--input", "-i", help="The yml file to extract from", required=True)
@click.option(
    "--output", "-o", required=True, help="The output file to write the code to"
)
@click.option(
    "--no-demisto-mock",
    help="Don't add an import for demisto mock, false by default",
    is_flag=True,
    show_default=True,
)
@click.option(
    "--no-common-server",
    help="Don't add an import for CommonServerPython."
    "If not specified will import unless this is CommonServerPython",
    is_flag=True,
    show_default=True,
)
@pass_config
@click.pass_context
@logging_setup_decorator
def extract_code(ctx, config, **kwargs):
    """Extract code from a Demisto integration or script yaml file."""
    from demisto_sdk.commands.split.ymlsplitter import YmlSplitter

    check_configuration_file("extract-code", kwargs)
    file_type: FileType = find_type(kwargs.get("input", ""), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT]:
        logger.info("[red]File is not an Integration or Script.[/red]")
        return 1
    extractor = YmlSplitter(
        configuration=config.configuration, file_type=file_type.value, **kwargs
    )
    return extractor.extract_code(kwargs["outfile"])


# ====================== prepare-content ====================== #
@main.command(name="prepare-content")
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    help="Comma-separated list of paths to directories or files to unify.",
    required=False,
    type=PathsParamType(dir_okay=True, exists=True),
)
@click.option(
    "-a",
    "--all",
    is_flag=True,
    help="Run prepare-content on all content packs. If no output path is given, will dump the result in the current working path.",
)
@click.option(
    "-g",
    "--graph",
    help="Whether use the content graph",
    is_flag=True,
    default=False,
)
@click.option(
    "--skip-update",
    help="Whether to skip updating the content graph (used only when graph is true)",
    is_flag=True,
    default=False,
)
@click.option(
    "-o", "--output", help="The output dir to write the unified yml to", required=False
)
@click.option(
    "-c",
    "--custom",
    help="Add test label to unified yml id/name/display",
    required=False,
)
@click.option(
    "-f",
    "--force",
    help="Forcefully overwrites the preexisting yml if one exists",
    is_flag=True,
    show_default=False,
)
@click.option(
    "-ini",
    "--ignore-native-image",
    help="Whether to ignore the addition of the nativeimage key to the yml of a script/integration",
    is_flag=True,
    show_default=False,
    default=False,
)
@click.option(
    "-mp",
    "--marketplace",
    help="The marketplace the content items are created for, that determines usage of marketplace "
    "unique text. Default is the XSOAR marketplace.",
    default="xsoar",
    type=click.Choice([mp.value for mp in list(MarketplaceVersions)] + ["v2"]),
)
@click.pass_context
@logging_setup_decorator
def prepare_content(ctx, **kwargs):
    """
    This command is used to prepare the content to be used in the platform.
    """
    assert (
        sum([bool(kwargs["all"]), bool(kwargs["input"])]) == 1
    ), "Exactly one of the '-a' or '-i' parameters must be provided."

    if kwargs["all"]:
        content_DTO = ContentDTO.from_path()
        output_path = kwargs.get("output", ".") or "."
        content_DTO.dump(
            dir=Path(output_path, "prepare-content-tmp"),
            marketplace=parse_marketplace_kwargs(kwargs),
        )
        return 0

    inputs = []
    if input_ := kwargs["input"]:
        inputs = input_.split(",")

    if output_path := kwargs["output"]:
        if "." in Path(output_path).name:  # check if the output path is a file
            if len(inputs) > 1:
                raise ValueError(
                    "When passing multiple inputs, the output path should be a directory and not a file."
                )
        else:
            dest_path = Path(output_path)
            dest_path.mkdir(exist_ok=True)

    for input_content in inputs:
        if output_path and len(inputs) > 1:
            path_name = Path(input_content).name
            kwargs["output"] = str(Path(output_path, path_name))

        if click.get_current_context().info_name == "unify":
            kwargs["unify_only"] = True

        check_configuration_file("unify", kwargs)
        # Input is of type Path.
        kwargs["input"] = str(input_content)
        file_type = find_type(kwargs["input"])
        if marketplace := kwargs.get("marketplace"):
            os.environ[ENV_DEMISTO_SDK_MARKETPLACE] = marketplace.lower()
        if file_type == FileType.GENERIC_MODULE:
            from demisto_sdk.commands.prepare_content.generic_module_unifier import (
                GenericModuleUnifier,
            )

            # pass arguments to GenericModule unifier and call the command
            generic_module_unifier = GenericModuleUnifier(**kwargs)
            generic_module_unifier.merge_generic_module_with_its_dashboards()
        else:
            PrepareUploadManager.prepare_for_upload(**kwargs)
    return 0


main.add_command(prepare_content, name="unify")


# ====================== zip-packs ====================== #


@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    help="The packs to be zipped as csv list of pack paths.",
    type=PathsParamType(exists=True, resolve_path=True),
    required=True,
)
@click.option(
    "-o",
    "--output",
    help="The destination directory to create the packs.",
    type=click.Path(file_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    "-v",
    "--content-version",
    help="The content version in CommonServerPython.",
    default="0.0.0",
)
@click.option(
    "-u",
    "--upload",
    is_flag=True,
    help="Upload the unified packs to the marketplace.",
    default=False,
)
@click.option(
    "--zip-all", is_flag=True, help="Zip all the packs in one zip file.", default=False
)
@click.pass_context
@logging_setup_decorator
def zip_packs(ctx, **kwargs) -> int:
    """Generating zipped packs that are ready to be uploaded to Cortex XSOAR machine."""
    from demisto_sdk.commands.upload.uploader import Uploader
    from demisto_sdk.commands.zip_packs.packs_zipper import (
        EX_FAIL,
        EX_SUCCESS,
        PacksZipper,
    )

    check_configuration_file("zip-packs", kwargs)

    # if upload is true - all zip packs will be compressed to one zip file
    should_upload = kwargs.pop("upload", False)
    zip_all = kwargs.pop("zip_all", False) or should_upload
    marketplace = parse_marketplace_kwargs(kwargs)

    packs_zipper = PacksZipper(
        zip_all=zip_all, pack_paths=kwargs.pop("input"), quiet_mode=zip_all, **kwargs
    )
    zip_path, unified_pack_names = packs_zipper.zip_packs()

    if should_upload and zip_path:
        return Uploader(
            input=Path(zip_path), pack_names=unified_pack_names, marketplace=marketplace
        ).upload()

    return EX_SUCCESS if zip_path is not None else EX_FAIL


# ====================== validate ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "--no-conf-json",
    is_flag=True,
    default=False,
    show_default=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Skip conf.json validation.",
)
@click.option(
    "-s",
    "--id-set",
    is_flag=True,
    default=False,
    show_default=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Perform validations using the id_set file.",
)
@click.option(
    "-idp",
    "--id-set-path",
    help="Relevant only for the old validate flow and will be removed in a future release. The path of the id-set.json used for validations.",
    type=click.Path(resolve_path=True),
)
@click.option(
    "-gr",
    "--graph",
    is_flag=True,
    default=False,
    show_default=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Perform validations on content graph.",
)
@click.option(
    "--prev-ver", help="Previous branch or SHA1 commit to run checks against."
)
@click.option(
    "--no-backward-comp",
    is_flag=True,
    show_default=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Whether to check backward compatibility or not.",
)
@click.option(
    "-g",
    "--use-git",
    is_flag=True,
    show_default=True,
    default=False,
    help="Validate changes using git - this will check current branch's changes against origin/master or origin/main. "
    "If the --post-commit flag is supplied: validation will run only on the current branch's changed files "
    "that have been committed. "
    "If the --post-commit flag is not supplied: validation will run on all changed files in the current branch, "
    "both committed and not committed. ",
)
@click.option(
    "-pc",
    "--post-commit",
    is_flag=True,
    help="Whether the validation should run only on the current branch's committed changed files. "
    "This applies only when the -g flag is supplied.",
)
@click.option(
    "-st",
    "--staged",
    is_flag=True,
    help="Whether the validation should ignore unstaged files."
    "This applies only when the -g flag is supplied.",
)
@click.option(
    "-iu",
    "--include-untracked",
    is_flag=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Whether to include untracked files in the validation. "
    "This applies only when the -g flag is supplied.",
)
@click.option(
    "-a",
    "--validate-all",
    is_flag=True,
    show_default=True,
    default=False,
    help="Whether to run all validation on all files or not.",
)
@click.option(
    "-i",
    "--input",
    type=PathsParamType(
        exists=True, resolve_path=True
    ),  # PathsParamType allows passing a list of paths
    help="The path of the content pack/file to validate specifically.",
)
@click.option(
    "--skip-pack-release-notes",
    is_flag=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Skip validation of pack release notes.",
)
@click.option(
    "--print-ignored-errors",
    is_flag=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Print ignored errors as warnings.",
)
@click.option(
    "--print-ignored-files",
    is_flag=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Print which files were ignored by the command.",
)
@click.option(
    "--no-docker-checks",
    is_flag=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Whether to run docker image validation.",
)
@click.option(
    "--silence-init-prints",
    is_flag=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Whether to skip the initialization prints.",
)
@click.option(
    "--skip-pack-dependencies",
    is_flag=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Skip validation of pack dependencies.",
)
@click.option(
    "--create-id-set",
    is_flag=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Whether to create the id_set.json file.",
)
@click.option(
    "-j",
    "--json-file",
    help="The JSON file path to which to output the command results.",
)
@click.option(
    "--skip-schema-check",
    is_flag=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Whether to skip the file schema check.",
)
@click.option(
    "--debug-git",
    is_flag=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Whether to print debug logs for git statuses.",
)
@click.option(
    "--print-pykwalify",
    is_flag=True,
    help="Relevant only for the old validate flow and will be removed in a future release. Whether to print the pykwalify log errors.",
)
@click.option(
    "--quiet-bc-validation",
    help="Relevant only for the old validate flow and will be removed in a future release. Set backwards compatibility validation's errors as warnings.",
    is_flag=True,
)
@click.option(
    "--allow-skipped",
    help="Relevant only for the old validate flow and will be removed in a future release. Don't fail on skipped integrations or when all test playbooks are skipped.",
    is_flag=True,
)
@click.option(
    "--no-multiprocessing",
    help="Relevant only for the old validate flow and will be removed in a future release. run validate all without multiprocessing, for debugging purposes.",
    is_flag=True,
    default=False,
)
@click.option(
    "-sv",
    "--run-specific-validations",
    help="Relevant only for the old validate flow and will be removed in a future release. Run specific validations by stating the error codes.",
    is_flag=False,
)
@click.option(
    "--category-to-run",
    help="Run specific validations by stating category they're listed under in the config file.",
    is_flag=False,
)
@click.option(
    "-f",
    "--fix",
    help="Wether to autofix failing validations with an available auto fix or not.",
    is_flag=True,
    default=False,
)
@click.option(
    "--config-path",
    help="Path for a config file to run, if not given - will run the default config at https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/validate/default_config.toml",
    is_flag=False,
)
@click.option(
    "--ignore-support-level",
    is_flag=True,
    show_default=True,
    default=False,
    help="Wether to skip validations based on their support level or not.",
)
@click.option(
    "--skip-old-validate",
    is_flag=True,
    show_default=True,
    default=False,
    help="Wether to skip the old validate flow.",
)
@click.option(
    "--run-new-validate",
    is_flag=True,
    show_default=True,
    default=False,
    help="Wether to run the new validate flow.",
)
@click.argument("file_paths", nargs=-1, type=click.Path(exists=True, resolve_path=True))
@pass_config
@click.pass_context
@logging_setup_decorator
def validate(ctx, config, file_paths: str, **kwargs):
    """Validate your content files. If no additional flags are given, will validated only committed files."""
    from demisto_sdk.commands.validate.old_validate_manager import OldValidateManager
    from demisto_sdk.commands.validate.validate_manager import ValidateManager

    if is_sdk_defined_working_offline():
        logger.error(SDK_OFFLINE_ERROR_MESSAGE)
        sys.exit(1)

    if file_paths and not kwargs["input"]:
        # If file_paths is given as an argument, use it as the file_paths input (instead of the -i flag). If both, input wins.
        kwargs["input"] = ",".join(file_paths)
    run_with_mp = not kwargs.pop("no_multiprocessing")
    check_configuration_file("validate", kwargs)
    sys.path.append(config.configuration.env_dir)

    file_path = kwargs["input"]

    if kwargs["post_commit"] and kwargs["staged"]:
        logger.info(
            "[red]Could not supply the staged flag with the post-commit flag[/red]"
        )
        sys.exit(1)
    try:
        is_external_repo = is_external_repository()
        # default validate to -g --post-commit
        if not kwargs.get("validate_all") and not kwargs["use_git"] and not file_path:
            kwargs["use_git"] = True
            kwargs["post_commit"] = True
        exit_code = 0
        if not kwargs["skip_old_validate"]:
            validator = OldValidateManager(
                is_backward_check=not kwargs["no_backward_comp"],
                only_committed_files=kwargs["post_commit"],
                prev_ver=kwargs["prev_ver"],
                skip_conf_json=kwargs["no_conf_json"],
                use_git=kwargs["use_git"],
                file_path=file_path,
                validate_all=kwargs.get("validate_all"),
                validate_id_set=kwargs["id_set"],
                validate_graph=kwargs.get("graph"),
                skip_pack_rn_validation=kwargs["skip_pack_release_notes"],
                print_ignored_errors=kwargs["print_ignored_errors"],
                is_external_repo=is_external_repo,
                print_ignored_files=kwargs["print_ignored_files"],
                no_docker_checks=kwargs["no_docker_checks"],
                silence_init_prints=kwargs["silence_init_prints"],
                skip_dependencies=kwargs["skip_pack_dependencies"],
                id_set_path=kwargs.get("id_set_path"),
                staged=kwargs["staged"],
                create_id_set=kwargs.get("create_id_set"),
                json_file_path=kwargs.get("json_file"),
                skip_schema_check=kwargs.get("skip_schema_check"),
                debug_git=kwargs.get("debug_git"),
                include_untracked=kwargs.get("include_untracked"),
                quiet_bc=kwargs.get("quiet_bc_validation"),
                multiprocessing=run_with_mp,
                check_is_unskipped=not kwargs.get("allow_skipped", False),
                specific_validations=kwargs.get("run_specific_validations"),
            )
            exit_code += validator.run_validation()
        if kwargs["run_new_validate"]:
            validation_results = ResultWriter(
                json_file_path=kwargs.get("json_file"),
            )
            config_reader = ConfigReader(
                config_file_path=kwargs.get("config_path"),
                category_to_run=kwargs.get("category_to_run"),
            )
            initializer = Initializer(
                use_git=kwargs["use_git"],
                staged=kwargs["staged"],
                committed_only=kwargs["post_commit"],
                prev_ver=kwargs["prev_ver"],
                file_path=file_path,
                all_files=kwargs.get("validate_all"),
            )
            validator_v2 = ValidateManager(
                file_path=file_path,
                validate_all=kwargs.get("validate_all"),
                initializer=initializer,
                validation_results=validation_results,
                config_reader=config_reader,
                allow_autofix=kwargs.get("fix"),
                ignore_support_level=kwargs.get("ignore_support_level"),
            )
            exit_code += validator_v2.run_validations()
        return exit_code
    except (git.InvalidGitRepositoryError, git.NoSuchPathError, FileNotFoundError) as e:
        logger.info(f"[red]{e}[/red]")
        logger.info(
            "\n[red]You may not be running `demisto-sdk validate` command in the content directory.\n"
            "Please run the command from content directory[red]"
        )
        sys.exit(1)


# ====================== create-content-artifacts ====================== #
@main.command(hidden=True)
@click.help_option("-h", "--help")
@click.option(
    "-a",
    "--artifacts_path",
    help="Destination directory to create the artifacts.",
    type=click.Path(file_okay=False, resolve_path=True),
    required=True,
)
@click.option("--zip/--no-zip", help="Zip content artifacts folders", default=True)
@click.option(
    "--packs",
    help="Create only content_packs artifacts. "
    "Used for server version 5.5.0 and earlier.",
    is_flag=True,
)
@click.option(
    "-v",
    "--content_version",
    help="The content version in CommonServerPython.",
    default="0.0.0",
)
@click.option(
    "-s",
    "--suffix",
    help="Suffix to add all yaml/json/yml files in the created artifacts.",
)
@click.option(
    "--cpus",
    help="Number of cpus/vcpus available - only required when os not reflect number of cpus (CircleCI"
    "always show 32, but medium has 3.",
    hidden=True,
    default=cpu_count(),
)
@click.option(
    "-idp",
    "--id-set-path",
    help="The full path of id_set.json",
    hidden=True,
    type=click.Path(exists=True, resolve_path=True),
)
@click.option(
    "-p",
    "--pack-names",
    help=(
        "Packs to create artifacts for. Optional values are: `all` or "
        "csv list of packs. "
        "Default is set to `all`"
    ),
    default="all",
    hidden=True,
)
@click.option(
    "-sk",
    "--signature-key",
    help="Base64 encoded signature key used for signing packs.",
    hidden=True,
)
@click.option(
    "-sd",
    "--sign-directory",
    help="Path to the signDirectory executable file.",
    type=click.Path(exists=True, resolve_path=True),
    hidden=True,
)
@click.option(
    "-rt",
    "--remove-test-playbooks",
    is_flag=True,
    help="Should remove test playbooks from content packs or not.",
    default=True,
    hidden=True,
)
@click.option(
    "-mp",
    "--marketplace",
    help="The marketplace the artifacts are created for, that "
    "determines which artifacts are created for each pack. "
    "Default is the XSOAR marketplace, that has all of the packs "
    "artifacts.",
    default="xsoar",
    type=click.Choice(["xsoar", "marketplacev2", "v2", "xpanse"]),
)
@click.option(
    "-fbi",
    "--filter-by-id-set",
    is_flag=True,
    help="Whether to use the id set as content items guide, meaning only include in the packs the "
    "content items that appear in the id set.",
    default=False,
    hidden=True,
)
@click.option(
    "-af",
    "--alternate-fields",
    is_flag=True,
    help="Use the alternative fields if such are present in the yml or json of the content item.",
    default=False,
    hidden=True,
)
@click.pass_context
@logging_setup_decorator
def create_content_artifacts(ctx, **kwargs) -> int:
    """Generating the following artifacts:
    1. content_new - Contains all content objects of type json,yaml (from_version < 6.0.0)
    2. content_packs - Contains all packs from Packs - Ignoring internal files (to_version >= 6.0.0).
    3. content_test - Contains all test scripts/playbooks (from_version < 6.0.0)
    4. content_all - Contains all from content_new and content_test.
    5. uploadable_packs - Contains zipped packs that are ready to be uploaded to Cortex XSOAR machine.
    """
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
        ArtifactsManager,
    )

    check_configuration_file("create-content-artifacts", kwargs)
    if marketplace := kwargs.get("marketplace"):
        os.environ[ENV_DEMISTO_SDK_MARKETPLACE] = marketplace.lower()
    artifacts_conf = ArtifactsManager(**kwargs)
    return artifacts_conf.create_content_artifacts()


# ====================== secrets ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option("-i", "--input", help="Specify file of to check secret on.")
@click.option(
    "--post-commit",
    is_flag=True,
    show_default=True,
    help="Whether the secretes is done after you committed your files, "
    "this will help the command to determine which files it should check in its "
    "run. Before you commit the files it should not be used. Mostly for build "
    "validations.",
)
@click.option(
    "-ie",
    "--ignore-entropy",
    is_flag=True,
    help="Ignore entropy algorithm that finds secret strings (passwords/api keys).",
)
@click.option(
    "-wl",
    "--whitelist",
    default="./Tests/secrets_white_list.json",
    show_default=True,
    help='Full path to whitelist file, file name should be "secrets_white_list.json"',
)
@click.option("--prev-ver", help="The branch against which to run secrets validation.")
@click.argument("file_paths", nargs=-1, type=click.Path(exists=True, resolve_path=True))
@pass_config
@click.pass_context
@logging_setup_decorator
def secrets(ctx, config, file_paths: str, **kwargs):
    """Run Secrets validator to catch sensitive data before exposing your code to public repository.
    Attach path to whitelist to allow manual whitelists.
    """
    if file_paths and not kwargs["input"]:
        # If file_paths is given as an argument, use it as the file_paths input (instead of the -i flag). If both, input wins.
        kwargs["input"] = ",".join(file_paths)

    from demisto_sdk.commands.secrets.secrets import SecretsValidator

    check_configuration_file("secrets", kwargs)
    sys.path.append(config.configuration.env_dir)
    secrets_validator = SecretsValidator(
        configuration=config.configuration,
        is_circle=kwargs["post_commit"],
        ignore_entropy=kwargs["ignore_entropy"],
        white_list_path=kwargs["whitelist"],
        input_path=kwargs.get("input"),
    )
    return secrets_validator.run()


# ====================== lint ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    help="Specify directory(s) of integration/script",
    type=PathsParamType(exists=True, resolve_path=True),
)
@click.option("-g", "--git", is_flag=True, help="Will run only on changed packages")
@click.option(
    "-a",
    "--all-packs",
    is_flag=True,
    help="Run lint on all directories in content repo",
)
@click.option(
    "-p",
    "--parallel",
    default=1,
    help="Run tests in parallel",
    type=click.IntRange(0, 15, clamp=True),
    show_default=True,
)
@click.option("--no-flake8", is_flag=True, help="Do NOT run flake8 linter")
@click.option("--no-bandit", is_flag=True, help="Do NOT run bandit linter")
@click.option("--no-xsoar-linter", is_flag=True, help="Do NOT run XSOAR linter")
@click.option("--no-mypy", is_flag=True, help="Do NOT run mypy static type checking")
@click.option("--no-vulture", is_flag=True, help="Do NOT run vulture linter")
@click.option("--no-pylint", is_flag=True, help="Do NOT run pylint linter")
@click.option("--no-test", is_flag=True, help="Do NOT test (skip pytest)")
@click.option("--no-pwsh-analyze", is_flag=True, help="Do NOT run powershell analyze")
@click.option("--no-pwsh-test", is_flag=True, help="Do NOT run powershell test")
@click.option("-kc", "--keep-container", is_flag=True, help="Keep the test container")
@click.option(
    "--prev-ver",
    help="Previous branch or SHA1 commit to run checks against",
    default=os.getenv("DEMISTO_DEFAULT_BRANCH", default="master"),
)
@click.option(
    "--test-xml",
    help="Path to store pytest xml results",
    type=click.Path(exists=True, resolve_path=True),
)
@click.option(
    "--failure-report",
    help="Path to store failed packs report",
    type=click.Path(exists=True, resolve_path=True),
)
@click.option(
    "-j",
    "--json-file",
    help="The JSON file path to which to output the command results.",
    type=click.Path(resolve_path=True),
)
@click.option("--no-coverage", is_flag=True, help="Do NOT run coverage report.")
@click.option(
    "--coverage-report",
    help="Specify directory for the coverage report files",
    type=PathsParamType(),
)
@click.option(
    "-dt",
    "--docker-timeout",
    default=60,
    help="The timeout (in seconds) for requests done by the docker client.",
    type=int,
)
@click.option(
    "-di",
    "--docker-image",
    default="from-yml",
    help="The docker image to check package on. Can be a comma separated list of Possible values: 'native:maintenance', 'native:ga', 'native:dev',"
    " 'all', a specific docker image from Docker Hub (e.g devdemisto/python3:3.10.9.12345) or the default"
    " 'from-yml', 'native:target'. To run lint only on native supported content with a specific image,"
    " use 'native:target' with --docker-image-target <specific-image>.",
)
@click.option(
    "-dit",
    "--docker-image-target",
    default="",
    help="The docker image to lint native supported content with. Should only be used with "
    "--docker-image native:target. An error will be raised otherwise.",
)
@click.option(
    "-cdam",
    "--check-dependent-api-module",
    is_flag=True,
    help="Run unit tests and lint on all packages that "
    "are dependent on the found "
    "modified api modules.",
    default=False,
)
@click.option(
    "--time-measurements-dir",
    help="Specify directory for the time measurements report file",
    type=PathsParamType(),
)
@click.pass_context
@logging_setup_decorator
def lint(ctx, **kwargs):
    """Lint command will perform:
    1. Package in host checks - flake8, bandit, mypy, vulture.
    2. Package in docker image checks -  pylint, pytest, powershell - test, powershell - analyze.
    Meant to be used with integrations/scripts that use the folder (package) structure.
    Will lookup up what docker image to use and will setup the dev dependencies and file in the target folder.
    If no additional flags specifying the packs are given, will lint only changed files.
    """
    from demisto_sdk.commands.lint.lint_manager import LintManager

    check_configuration_file("lint", kwargs)
    lint_manager = LintManager(
        input=kwargs.get("input"),  # type: ignore[arg-type]
        git=kwargs.get("git"),  # type: ignore[arg-type]
        all_packs=kwargs.get("all_packs"),  # type: ignore[arg-type]
        prev_ver=kwargs.get("prev_ver"),  # type: ignore[arg-type]
        json_file_path=kwargs.get("json_file"),  # type: ignore[arg-type]
        check_dependent_api_module=kwargs.get("check_dependent_api_module"),  # type: ignore[arg-type]
    )
    return lint_manager.run(
        parallel=kwargs.get("parallel"),  # type: ignore[arg-type]
        no_flake8=kwargs.get("no_flake8"),  # type: ignore[arg-type]
        no_bandit=kwargs.get("no_bandit"),  # type: ignore[arg-type]
        no_mypy=kwargs.get("no_mypy"),  # type: ignore[arg-type]
        no_vulture=kwargs.get("no_vulture"),  # type: ignore[arg-type]
        no_xsoar_linter=kwargs.get("no_xsoar_linter"),  # type: ignore[arg-type]
        no_pylint=kwargs.get("no_pylint"),  # type: ignore[arg-type]
        no_test=kwargs.get("no_test"),  # type: ignore[arg-type]
        no_pwsh_analyze=kwargs.get("no_pwsh_analyze"),  # type: ignore[arg-type]
        no_pwsh_test=kwargs.get("no_pwsh_test"),  # type: ignore[arg-type]
        keep_container=kwargs.get("keep_container"),  # type: ignore[arg-type]
        test_xml=kwargs.get("test_xml"),  # type: ignore[arg-type]
        failure_report=kwargs.get("failure_report"),  # type: ignore[arg-type]
        no_coverage=kwargs.get("no_coverage"),  # type: ignore[arg-type]
        coverage_report=kwargs.get("coverage_report"),  # type: ignore[arg-type]
        docker_timeout=kwargs.get("docker_timeout"),  # type: ignore[arg-type]
        docker_image_flag=kwargs.get("docker_image"),  # type: ignore[arg-type]
        docker_image_target=kwargs.get("docker_image_target"),  # type: ignore[arg-type]
        time_measurements_dir=kwargs.get("time_measurements_dir"),  # type: ignore[arg-type]
    )


# ====================== coverage-analyze ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    help="The .coverage file to analyze.",
    default=os.path.join("coverage_report", ".coverage"),
    type=PathsParamType(resolve_path=True),
)
@click.option(
    "--default-min-coverage",
    help="Default minimum coverage (for new files).",
    default=70.0,
    type=click.FloatRange(0.0, 100.0),
)
@click.option(
    "--allowed-coverage-degradation-percentage",
    help="Allowed coverage degradation percentage (for modified files).",
    default=1.0,
    type=click.FloatRange(0.0, 100.0),
)
@click.option(
    "--no-cache",
    help="Force download of the previous coverage report file.",
    is_flag=True,
    type=bool,
)
@click.option(
    "--report-dir",
    help="Directory of the coverage report files.",
    default="coverage_report",
    type=PathsParamType(resolve_path=True),
)
@click.option(
    "--report-type",
    help="The type of coverage report (posible values: 'text', 'html', 'xml', 'json' or 'all').",
    type=str,
)
@click.option(
    "--no-min-coverage-enforcement",
    help="Do not enforce minimum coverage.",
    is_flag=True,
)
@click.option(
    "--previous-coverage-report-url",
    help="URL of the previous coverage report.",
    default=f"https://storage.googleapis.com/{DEMISTO_SDK_MARKETPLACE_XSOAR_DIST_DEV}/code-coverage-reports/coverage-min.json",
    type=str,
)
@click.pass_context
@logging_setup_decorator
def coverage_analyze(ctx, **kwargs):
    from demisto_sdk.commands.coverage_analyze.coverage_report import CoverageReport

    try:
        no_degradation_check = (
            kwargs["allowed_coverage_degradation_percentage"] == 100.0
        )
        no_min_coverage_enforcement = kwargs["no_min_coverage_enforcement"]

        cov_report = CoverageReport(
            default_min_coverage=kwargs["default_min_coverage"],
            allowed_coverage_degradation_percentage=kwargs[
                "allowed_coverage_degradation_percentage"
            ],
            coverage_file=kwargs["input"],
            no_cache=kwargs.get("no_cache", False),
            report_dir=kwargs["report_dir"],
            report_type=kwargs["report_type"],
            no_degradation_check=no_degradation_check,
            previous_coverage_report_url=kwargs["previous_coverage_report_url"],
        )
        cov_report.coverage_report()
        # if no_degradation_check=True we will suppress the minimum coverage check
        if (
            no_degradation_check
            or cov_report.coverage_diff_report()
            or no_min_coverage_enforcement
        ):
            return 0
    except FileNotFoundError as e:
        logger.warning(e)
        return 0
    except Exception as error:
        logger.error(error)

    return 1


# ====================== format ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    help="The path of the script yml file or a comma separated list\n"
    "If no input is specified, the format will be executed on all new/changed files.",
    type=PathsParamType(
        exists=True, resolve_path=True
    ),  # PathsParamType allows passing a list of paths
)
@click.option(
    "-o",
    "--output",
    help="The path where the formatted file will be saved to",
    type=click.Path(resolve_path=True),
)
@click.option("-fv", "--from-version", help="Specify fromversion of the pack")
@click.option(
    "-nv", "--no-validate", help="Set when validate on file is not wanted", is_flag=True
)
@click.option(
    "-ud",
    "--update-docker",
    help="Set if you want to update the docker image of the integration/script",
    is_flag=True,
)
@click.option(
    "-y/-n",
    "--assume-yes/--assume-no",
    help="Automatic yes/no to prompts; assume 'yes'/'no' as answer to all prompts and run non-interactively",
    is_flag=True,
    default=None,
)
@click.option(
    "-d",
    "--deprecate",
    help="Set if you want to deprecate the integration/script/playbook",
    is_flag=True,
)
@click.option(
    "-g",
    "--use-git",
    help="Use git to automatically recognize which files changed and run format on them.",
    is_flag=True,
)
@click.option(
    "--prev-ver", help="Previous branch or SHA1 commit to run checks against."
)
@click.option(
    "-iu",
    "--include-untracked",
    is_flag=True,
    help="Whether to include untracked files in the formatting.",
)
@click.option(
    "-at",
    "--add-tests",
    is_flag=True,
    help="Whether to answer manually to add tests configuration prompt when running interactively.",
)
@click.option(
    "-s",
    "--id-set-path",
    help="Deprecated. The path of the id_set json file.",
    type=click.Path(exists=True, resolve_path=True),
)
@click.option(
    "-gr/-ngr",
    "--graph/--no-graph",
    help="Whether to use the content graph or not.",
    is_flag=True,
    default=True,
)
@click.argument("file_paths", nargs=-1, type=click.Path(exists=True, resolve_path=True))
@click.pass_context
@logging_setup_decorator
def format(
    ctx,
    input: str,
    output: Path,
    from_version: str,
    no_validate: bool,
    update_docker: bool,
    assume_yes: Union[None, bool],
    deprecate: bool,
    use_git: bool,
    prev_ver: str,
    include_untracked: bool,
    add_tests: bool,
    id_set_path: str,
    file_paths: Tuple[str, ...],
    **kwargs,
):
    """Run formatter on a given script/playbook/integration/incidentfield/indicatorfield/
    incidenttype/indicatortype/layout/dashboard/classifier/mapper/widget/report file/genericfield/generictype/
    genericmodule/genericdefinition.
    """
    from demisto_sdk.commands.format.format_module import format_manager

    if is_sdk_defined_working_offline():
        logger.error(SDK_OFFLINE_ERROR_MESSAGE)
        sys.exit(1)

    if file_paths and not input:
        input = ",".join(file_paths)

    with ReadMeValidator.start_mdx_server():
        return format_manager(
            str(input) if input else None,
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
            id_set_path=id_set_path,
            use_graph=kwargs.get("graph", True),
        )


# ====================== upload ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    type=PathsParamType(exists=True, resolve_path=True),
    help="The path of file or a directory to upload. The following are supported:\n"
    "- Pack\n"
    "- A content entity directory that is inside a pack. For example: an Integrations "
    "directory or a Layouts directory.\n"
    "- Valid file that can be imported to Cortex XSOAR manually. For example a playbook: "
    "helloWorld.yml",
    required=False,
)
@click.option(
    "--input-config-file",
    type=PathsParamType(exists=True, resolve_path=True),
    help="The path to the config file to download all the custom packs from",
    required=False,
)
@click.option(
    "-z/-nz",
    "--zip/--no-zip",
    help="Compress the pack to zip before upload, this flag is relevant only for packs.",
    is_flag=True,
    default=True,
)
@click.option(
    "-x",
    "--xsiam",
    help="Upload the pack to XSIAM server. Must be used together with -z",
    is_flag=True,
)
@click.option(
    "-mp",
    "--marketplace",
    help="The marketplace to which the content will be uploaded.",
)
@click.option(
    "--keep-zip",
    help="Directory where to store the zip after creation, this argument is relevant only for packs "
    "and in case the --zip flag is used.",
    required=False,
    type=click.Path(exists=True),
)
@click.option("--insecure", help="Skip certificate validation", is_flag=True)
@click.option(
    "--skip_validation",
    is_flag=True,
    help="Only for upload zipped packs, "
    "if true will skip upload packs validation, use just when migrate existing custom content to packs.",
)
@click.option(
    "--reattach",
    help="Reattach the detached files in the XSOAR instance"
    "for the CI/CD Flow. If you set the --input-config-file flag, "
    "any detached item in your XSOAR instance that isn't currently in the repo's SystemPacks folder "
    "will be re-attached.)",
    is_flag=True,
)
@click.option(
    "--override-existing",
    is_flag=True,
    help="This value (True/False) determines if the user should be presented with a confirmation prompt when "
    "attempting to upload a content pack that is already installed on the Cortex XSOAR server. This allows the upload "
    "command to be used within non-interactive shells.",
)
@click.pass_context
@logging_setup_decorator
def upload(ctx, **kwargs):
    """Upload integration or pack to Demisto instance.
    DEMISTO_BASE_URL environment variable should contain the Demisto server base URL.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    * Note: Uploading classifiers to Cortex XSOAR is available from version 6.0.0 and up. *
    """
    return upload_content_entity(**kwargs)


# ====================== download ====================== #


@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-o",
    "--output",
    help="A path to a pack directory to download content to.",
    required=False,
    multiple=False,
)
@click.option(
    "-i",
    "--input",
    help="Name of a custom content item to download. The flag can be used multiple times to download multiple files.",
    required=False,
    multiple=True,
)
@click.option(
    "-r",
    "--regex",
    help="Download all custom content items matching this RegEx pattern.",
    required=False,
)
@click.option("--insecure", help="Skip certificate validation", is_flag=True)
@click.option(
    "-f",
    "--force",
    help="If downloaded content already exists in the output directory, overwrite it. ",
    is_flag=True,
)
@click.option(
    "-lf",
    "--list-files",
    help="List all custom content items available to download and exit.",
    is_flag=True,
)
@click.option(
    "-a",
    "--all-custom-content",
    help="Download all available custom content items.",
    is_flag=True,
)
@click.option(
    "-fmt",
    "--run-format",
    help="Format downloaded files.",
    is_flag=True,
)
@click.option("--system", help="Download system items", is_flag=True, default=False)
@click.option(
    "-it",
    "--item-type",
    help="Type of the content item to download. Required and used only when downloading system items.",
    type=click.Choice(
        [
            "IncidentType",
            "IndicatorType",
            "Field",
            "Layout",
            "Playbook",
            "Automation",
            "Classifier",
            "Mapper",
        ],
        case_sensitive=False,
    ),
)
@click.option(
    "--init",
    help="Initialize the output directory with a pack structure.",
    is_flag=True,
    default=False,
)
@click.option(
    "--keep-empty-folders",
    help="Keep empty folders when a pack structure is initialized.",
    is_flag=True,
    default=False,
)
@click.option(
    "--auto-replace-uuids/--no-auto-replace-uuids",
    help="Whether to replace UUID IDs (automatically assigned to custom content by the server) for downloaded custom content.",
    default=True,
)
@click.pass_context
@logging_setup_decorator
def download(ctx, **kwargs):
    """Download custom content from a Cortex XSOAR / XSIAM instance.
    DEMISTO_BASE_URL environment variable should contain the server base URL.
    DEMISTO_API_KEY environment variable should contain a valid API Key for the server.
    """
    from demisto_sdk.commands.download.downloader import Downloader

    check_configuration_file("download", kwargs)
    return Downloader(**kwargs).download()


# ====================== update-xsoar-config-file ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-pi",
    "--pack-id",
    help="The Pack ID to add to XSOAR Configuration File",
    required=False,
    multiple=False,
)
@click.option(
    "-pd",
    "--pack-data",
    help="The Pack Data to add to XSOAR Configuration File - "
    "Pack URL for Custom Pack and Pack Version for OOTB Pack",
    required=False,
    multiple=False,
)
@click.option(
    "-mp",
    "--add-marketplace-pack",
    help="Add a Pack to the MarketPlace Packs section in the Configuration File",
    required=False,
    is_flag=True,
)
@click.option(
    "-cp",
    "--add-custom-pack",
    help="Add the Pack to the Custom Packs section in the Configuration File",
    is_flag=True,
)
@click.option(
    "-all",
    "--add-all-marketplace-packs",
    help="Add all the installed MarketPlace Packs to the marketplace_packs in XSOAR Configuration File",
    is_flag=True,
)
@click.option("--insecure", help="Skip certificate validation", is_flag=True)
@click.option(
    "--file-path",
    help="XSOAR Configuration File path, the default value is in the repo level",
    is_flag=False,
)
@click.pass_context
@logging_setup_decorator
def xsoar_config_file_update(ctx, **kwargs):
    """Handle your XSOAR Configuration File.
    Add automatically all the installed MarketPlace Packs to the marketplace_packs section in XSOAR Configuration File.
    Add a Pack to both marketplace_packs and custom_packs sections in the Configuration File.
    """
    from demisto_sdk.commands.update_xsoar_config_file.update_xsoar_config_file import (
        XSOARConfigFileUpdater,
    )

    file_updater: XSOARConfigFileUpdater = XSOARConfigFileUpdater(**kwargs)
    return file_updater.update()


# ====================== run ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option("-q", "--query", help="The query to run", required=True)
@click.option("--insecure", help="Skip certificate validation", is_flag=True)
@click.option(
    "-id",
    "--incident-id",
    help="The incident to run the query on, if not specified the playground will be used.",
)
@click.option(
    "-D",
    "--debug",
    help="Whether to enable the debug-mode feature or not, if you want to save the output file "
    "please use the --debug-path option",
    is_flag=True,
)
@click.option(
    "--debug-path",
    help="The path to save the debug file at, if not specified the debug file will be printed to the "
    "terminal",
)
@click.option(
    "--json-to-outputs",
    help="Whether to run json_to_outputs command on the context output of the query. If the "
    "context output does not exists or the `-r` flag is used, will use the raw"
    " response of the query",
    is_flag=True,
)
@click.option(
    "-p",
    "--prefix",
    help="Used with `json-to-outputs` flag. Output prefix e.g. Jira.Ticket, VirusTotal.IP, "
    "the base path for the outputs that the script generates",
)
@click.option(
    "-r",
    "--raw-response",
    help="Used with `json-to-outputs` flag. Use the raw response of the query for"
    " `json-to-outputs`",
    is_flag=True,
)
@click.pass_context
@logging_setup_decorator
def run(ctx, **kwargs):
    """Run integration command on remote Demisto instance in the playground.
    DEMISTO_BASE_URL environment variable should contain the Demisto base URL.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    """
    from demisto_sdk.commands.run_cmd.runner import Runner

    check_configuration_file("run", kwargs)
    runner = Runner(**kwargs)
    return runner.run()


# ====================== run-playbook ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "--url",
    "-u",
    help="URL to a Demisto instance. If not provided, the url will be taken from DEMISTO_BASE_URL environment variable.",
)
@click.option("--playbook_id", "-p", help="The playbook ID to run.", required=True)
@click.option(
    "--wait",
    "-w",
    is_flag=True,
    help="Wait until the playbook run is finished and get a response.",
)
@click.option(
    "--timeout",
    "-t",
    default=90,
    show_default=True,
    help="Timeout to query for playbook's state. Relevant only if --wait has been passed.",
)
@click.option("--insecure", help="Skip certificate validation.", is_flag=True)
@click.pass_context
@logging_setup_decorator
def run_playbook(ctx, **kwargs):
    """Run a playbook in Demisto.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    Example: DEMISTO_API_KEY=<API KEY> demisto-sdk run-playbook -p 'p_name' -u
    'https://demisto.local'.
    """
    from demisto_sdk.commands.run_playbook.playbook_runner import PlaybookRunner

    check_configuration_file("run-playbook", kwargs)
    playbook_runner = PlaybookRunner(
        playbook_id=kwargs.get("playbook_id", ""),
        url=kwargs.get("url", ""),
        wait=kwargs.get("wait", False),
        timeout=kwargs.get("timeout", 90),
        insecure=kwargs.get("insecure", False),
    )
    return playbook_runner.run_playbook()


# ====================== run-test-playbook ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-tpb",
    "--test-playbook-path",
    help="Path to test playbook to run, "
    "can be a path to specific test playbook or path to pack name for example: Packs/GitHub.",
    required=False,
)
@click.option(
    "--all", is_flag=True, help="Run all the test playbooks from this repository."
)
@click.option(
    "--wait",
    "-w",
    is_flag=True,
    default=True,
    help="Wait until the test-playbook run is finished and get a response.",
)
@click.option(
    "--timeout",
    "-t",
    default=90,
    show_default=True,
    help="Timeout for the command. The test-playbook will continue to run in your instance",
)
@click.option("--insecure", help="Skip certificate validation.", is_flag=True)
@click.pass_context
@logging_setup_decorator
def run_test_playbook(ctx, **kwargs):
    """Run a test playbooks in your instance."""
    from demisto_sdk.commands.run_test_playbook.test_playbook_runner import (
        TestPlaybookRunner,
    )

    check_configuration_file("run-test-playbook", kwargs)
    test_playbook_runner = TestPlaybookRunner(**kwargs)
    return test_playbook_runner.manage_and_run_test_playbooks()


# ====================== generate-outputs ====================== #
@main.command(short_help="""Generates outputs (from json or examples).""")
@click.help_option("-h", "--help")
@click.option(
    "-c",
    "--command",
    help="Specific command name (e.g. xdr-get-incidents)",
    required=False,
)
@click.option(
    "-j",
    "--json",
    help="Valid JSON file path. If not specified, the script will wait for user input in the terminal. "
    "The response can be obtained by running the command with `raw-response=true` argument.",
    required=False,
)
@click.option(
    "-p",
    "--prefix",
    help="Output prefix like Jira.Ticket, VirusTotal.IP, the base path for the outputs that the "
    "script generates",
    required=False,
)
@click.option(
    "-o",
    "--output",
    help="Output file path, if not specified then will print to stdout",
    required=False,
)
@click.option(
    "--ai",
    is_flag=True,
    help="**Experimental** - Help generate context descriptions via AI transformers (must have a valid AI21 key at ai21.com)",
)
@click.option(
    "--interactive",
    help="If passed, then for each output field will ask user interactively to enter the "
    "description. By default is interactive mode is disabled. No need to use with --ai (it is already interactive)",
    is_flag=True,
)
@click.option(
    "-d",
    "--descriptions",
    help="A JSON or a path to a JSON file, mapping field names to their descriptions. "
    "If not specified, the script prompt the user to input the JSON content.",
    is_flag=True,
)
@click.option("-i", "--input", help="Valid YAML integration file path.", required=False)
@click.option(
    "-e",
    "--examples",
    help="Integrations: path for file containing command examples."
    " Each command should be in a separate line."
    " Scripts: the script example surrounded by quotes."
    " For example: -e '!ConvertFile entry_id=<entry_id>'",
)
@click.option(
    "--insecure",
    help="Skip certificate validation to run the commands in order to generate the docs.",
    is_flag=True,
)
@click.pass_context
@logging_setup_decorator
def generate_outputs(ctx, **kwargs):
    """Demisto integrations/scripts have a YAML file that defines them.
    Creating the YAML file is a tedious and error-prone task of manually copying outputs from the API result to the
    file/UI/PyCharm. This script auto generates the YAML for a command from the JSON result of the relevant API call
    In addition you can supply examples files and generate the context description directly in the YML from those examples.
    """
    from demisto_sdk.commands.generate_outputs.generate_outputs import (
        run_generate_outputs,
    )

    check_configuration_file("generate-outputs", kwargs)
    return run_generate_outputs(**kwargs)


# ====================== generate-test-playbook ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-i", "--input", required=True, help="Specify integration/script yml path"
)
@click.option(
    "-o",
    "--output",
    required=False,
    help="Specify output directory or path to an output yml file. "
    "If a path to a yml file is specified - it will be the output path.\n"
    "If a folder path is specified - a yml output will be saved in the folder.\n"
    "If not specified, and the input is located at `.../Packs/<pack_name>/Integrations`, "
    "the output will be saved under `.../Packs/<pack_name>/TestPlaybooks`.\n"
    "Otherwise (no folder in the input hierarchy is named `Packs`), "
    "the output will be saved in the current directory.",
)
@click.option(
    "-n",
    "--name",
    required=True,
    help="Specify test playbook name. The output file name will be `playbook-<name>_Test.yml",
)
@click.option(
    "--no-outputs",
    is_flag=True,
    help="Skip generating verification conditions for each output contextPath. Use when you want to decide which "
    "outputs to verify and which not",
)
@click.option(
    "-ab",
    "--all-brands",
    "use_all_brands",
    help="Generate a test-playbook which calls commands using integrations of all available brands. "
    "When not used, the generated playbook calls commands using instances of the provided integration brand.",
    is_flag=True,
)
@click.option(
    "-c",
    "--commands",
    help="A comma-separated command names to generate playbook tasks for, "
    "will ignore the rest of the commands."
    "e.g xdr-get-incidents,xdr-update-incident",
    required=False,
)
@click.option(
    "-e",
    "--examples",
    help="For integrations: path for file containing command examples."
    " Each command should be in a separate line."
    " For scripts: the script example surrounded by quotes."
    " For example: -e '!ConvertFile entry_id=<entry_id>'",
)
@click.option(
    "-u",
    "--upload",
    help="Whether to upload the test playbook after the generation.",
    is_flag=True,
)
@click.pass_context
@logging_setup_decorator
def generate_test_playbook(ctx, **kwargs):
    """Generate test playbook from integration or script"""
    from demisto_sdk.commands.generate_test_playbook.test_playbook_generator import (
        PlaybookTestsGenerator,
    )

    check_configuration_file("generate-test-playbook", kwargs)
    file_type: FileType = find_type(kwargs.get("input", ""), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT]:
        logger.info(
            "[red]Generating test playbook is possible only for an Integration or a Script.[/red]"
        )
        return 1

    try:
        generator = PlaybookTestsGenerator(file_type=file_type.value, **kwargs)
        if generator.run():
            sys.exit(0)
        sys.exit(1)
    except PlaybookTestsGenerator.InvalidOutputPathError as e:
        logger.info(f"[red]{e}[/red]")
        return 1


# ====================== init ====================== #


@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-n", "--name", help="The name of the directory and file you want to create"
)
@click.option("--id", help="The id used in the yml file of the integration or script")
@click.option(
    "-o",
    "--output",
    help="The output dir to write the object into. The default one is the current working "
    "directory.",
)
@click.option(
    "--integration",
    is_flag=True,
    help="Create an Integration based on BaseIntegration template",
)
@click.option(
    "--script", is_flag=True, help="Create a Script based on BaseScript example"
)
@click.option(
    "--xsiam",
    is_flag=True,
    help="Create an Event Collector based on a template, and create matching sub directories",
)
@click.option("--pack", is_flag=True, help="Create pack and its sub directories")
@click.option(
    "-t",
    "--template",
    help="Create an Integration/Script based on a specific template.\n"
    "Integration template options: HelloWorld, HelloIAMWorld, FeedHelloWorld.\n"
    "Script template options: HelloWorldScript",
)
@click.option(
    "-a",
    "--author-image",
    help="Path of the file 'Author_image.png'. \n "
    "Image will be presented in marketplace under PUBLISHER section. File should be up to 4kb and dimensions of 120x50",
)
@click.option(
    "--demisto_mock",
    is_flag=True,
    help="Copy the demistomock. Relevant for initialization of Scripts and Integrations within a Pack.",
)
@click.option(
    "--common-server",
    is_flag=True,
    help="Copy the CommonServerPython. Relevant for initialization of Scripts and Integrations within a Pack.",
)
@click.pass_context
@logging_setup_decorator
def init(ctx, **kwargs):
    """Initialize a new Pack, Integration or Script.
    If the script/integration flags are not present, we will create a pack with the given name.
    Otherwise when using the flags we will generate a script/integration based on your selection.
    """
    from demisto_sdk.commands.init.initiator import Initiator

    check_configuration_file("init", kwargs)
    marketplace = parse_marketplace_kwargs(kwargs)
    initiator = Initiator(marketplace=marketplace, **kwargs)
    initiator.init()
    return 0


# ====================== generate-docs ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option("-i", "--input", help="Path of the yml file.", required=True)
@click.option(
    "-o",
    "--output",
    help="The output dir to write the documentation file into,"
    " documentation file name is README.md. If not specified, will be in the yml dir.",
    required=False,
)
@click.option(
    "-uc",
    "--use_cases",
    help="For integration - Top use-cases. Number the steps by '*' (i.e. '* foo. * bar.')",
    required=False,
)
@click.option(
    "-c",
    "--command",
    help="A comma-separated command names to generate doc for, will ignore the rest of the commands."
    "e.g xdr-get-incidents,xdr-update-incident",
    required=False,
)
@click.option(
    "-e",
    "--examples",
    help="Integrations: path for file containing command examples."
    " Each command should be in a separate line."
    " Scripts: the script example surrounded by quotes."
    " For example: -e '!ConvertFile entry_id=<entry_id>'",
)
@click.option(
    "-p",
    "--permissions",
    type=click.Choice(["none", "general", "per-command"]),
    help="Permissions needed.",
    required=True,
    default="none",
)
@click.option(
    "-cp",
    "--command-permissions",
    help="Path for file containing commands permissions"
    " Each command permissions should be in a separate line."
    " (i.e. '<command-name> Administrator READ-WRITE')",
    required=False,
)
@click.option(
    "-l",
    "--limitations",
    help="Known limitations. Number the steps by '*' (i.e. '* foo. * bar.')",
    required=False,
)
@click.option(
    "--insecure",
    help="Skip certificate validation to run the commands in order to generate the docs.",
    is_flag=True,
)
@click.option("--old-version", help="Path of the old integration version yml file.")
@click.option(
    "--skip-breaking-changes",
    is_flag=True,
    help="Skip generating of breaking changes section.",
)
@click.option(
    "--custom-image-path",
    help="A custom path to a playbook image. If not stated, a default link will be added to the file.",
)
@click.option(
    "-rt",
    "--readme-template",
    help="The readme template that should be appended to the given README.md file",
    type=click.Choice(["syslog", "xdrc", "http-collector"]),
)
@click.option(
    "-gr/-ngr",
    "--graph/--no-graph",
    help="Whether to use the content graph or not.",
    is_flag=True,
    default=True,
)
@click.pass_context
@logging_setup_decorator
def generate_docs(ctx, **kwargs):
    """Generate documentation for integration, playbook or script from yaml file."""
    try:
        check_configuration_file("generate-docs", kwargs)
        input_path_str: str = kwargs.get("input", "")
        if not (input_path := Path(input_path_str)).exists():
            raise Exception(f"[red]input {input_path_str} does not exist[/red]")

        if (output_path := kwargs.get("output")) and not Path(output_path).is_dir():
            raise Exception(
                f"[red]Output directory {output_path} is not a directory.[/red]"
            )

        if input_path.is_file():
            if input_path.suffix.lower() not in {".yml", ".md"}:
                raise Exception(
                    f"[red]input {input_path} is not a valid yml or readme file.[/red]"
                )

            _generate_docs_for_file(kwargs)

        # Add support for input which is a Playbooks directory and not a single yml file
        elif input_path.is_dir() and input_path.name == "Playbooks":
            for yml in input_path.glob("*.yml"):
                file_kwargs = copy.deepcopy(kwargs)
                file_kwargs["input"] = str(yml)
                _generate_docs_for_file(file_kwargs)

        else:
            raise Exception(
                f"[red]Input {input_path} is neither a valid yml file, nor a folder named Playbooks, nor a readme file.[/red]"
            )

        return 0

    except Exception:
        logger.exception("Failed generating docs")
        sys.exit(1)


def _generate_docs_for_file(kwargs: Dict[str, Any]):
    """Helper function for supporting Playbooks directory as an input and not only a single yml file."""

    from demisto_sdk.commands.generate_docs.generate_integration_doc import (
        generate_integration_doc,
    )
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import (
        generate_playbook_doc,
    )
    from demisto_sdk.commands.generate_docs.generate_readme_template import (
        generate_readme_template,
    )
    from demisto_sdk.commands.generate_docs.generate_script_doc import (
        generate_script_doc,
    )

    # Extract all the necessary arguments
    input_path: str = kwargs.get("input", "")
    output_path = kwargs.get("output")
    command = kwargs.get("command")
    examples: str = kwargs.get("examples", "")
    permissions = kwargs.get("permissions")
    limitations = kwargs.get("limitations")
    insecure: bool = kwargs.get("insecure", False)
    old_version: str = kwargs.get("old_version", "")
    skip_breaking_changes: bool = kwargs.get("skip_breaking_changes", False)
    custom_image_path: str = kwargs.get("custom_image_path", "")
    readme_template: str = kwargs.get("readme_template", "")
    use_graph = kwargs.get("graph", True)

    try:
        if command:
            if (
                output_path
                and (not Path(output_path, "README.md").is_file())
                or (not output_path)
                and (
                    not Path(
                        os.path.dirname(os.path.realpath(input_path)), "README.md"
                    ).is_file()
                )
            ):
                raise Exception(
                    "[red]The `command` argument must be presented with existing `README.md` docs."
                )

        file_type = find_type(kwargs.get("input", ""), ignore_sub_categories=True)
        if file_type not in {
            FileType.INTEGRATION,
            FileType.SCRIPT,
            FileType.PLAYBOOK,
            FileType.README,
        }:
            raise Exception(
                "[red]File is not an Integration, Script, Playbook or a README.[/red]"
            )

        if old_version and not Path(old_version).is_file():
            raise Exception(
                f"[red]Input old version file {old_version} was not found.[/red]"
            )

        if old_version and not old_version.lower().endswith(".yml"):
            raise Exception(
                f"[red]Input old version {old_version} is not a valid yml file.[/red]"
            )

        if file_type == FileType.INTEGRATION:
            logger.info(f"Generating {file_type.value.lower()} documentation")
            use_cases = kwargs.get("use_cases")
            command_permissions = kwargs.get("command_permissions")
            return generate_integration_doc(
                input_path=input_path,
                output=output_path,
                use_cases=use_cases,
                examples=examples,
                permissions=permissions,
                command_permissions=command_permissions,
                limitations=limitations,
                insecure=insecure,
                command=command,
                old_version=old_version,
                skip_breaking_changes=skip_breaking_changes,
            )
        elif file_type == FileType.SCRIPT:
            logger.info(f"Generating {file_type.value.lower()} documentation")
            return generate_script_doc(
                input_path=input_path,
                output=output_path,
                examples=examples,
                permissions=permissions,
                limitations=limitations,
                insecure=insecure,
                use_graph=use_graph,
            )
        elif file_type == FileType.PLAYBOOK:
            logger.info(f"Generating {file_type.value.lower()} documentation")
            return generate_playbook_doc(
                input_path=input_path,
                output=output_path,
                permissions=permissions,
                limitations=limitations,
                custom_image_path=custom_image_path,
            )

        elif file_type == FileType.README:
            logger.info(f"Adding template to {file_type.value.lower()} file")
            return generate_readme_template(
                input_path=Path(input_path), readme_template=readme_template
            )

        else:
            raise Exception(f"[red]File type {file_type.value} is not supported.[/red]")

    except Exception:
        logger.exception(f"Failed generating docs for {input_path}")
        sys.exit(1)


# ====================== create-id-set ====================== #
@main.command(hidden=True)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    help="Input file path, the default is the content repo.",
    default="",
)
@click.option(
    "-o",
    "--output",
    help="Output file path, the default is the Tests directory.",
    default="",
)
@click.option(
    "-fd",
    "--fail-duplicates",
    help="Fails the process if any duplicates are found.",
    is_flag=True,
)
@click.option(
    "-mp",
    "--marketplace",
    help="The marketplace the id set are created for, that determines which packs are"
    " inserted to the id set, and which items are present in the id set for "
    "each pack. Default is all packs exists in the content repository.",
    default="",
)
@click.pass_context
@logging_setup_decorator
def create_id_set(ctx, **kwargs):
    """Create the content dependency tree by ids."""
    from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
    from demisto_sdk.commands.find_dependencies.find_dependencies import (
        remove_dependencies_from_id_set,
    )

    check_configuration_file("create-id-set", kwargs)
    id_set_creator = IDSetCreator(**kwargs)
    (
        id_set,
        excluded_items_by_pack,
        excluded_items_by_type,
    ) = id_set_creator.create_id_set()

    if excluded_items_by_pack:
        remove_dependencies_from_id_set(
            id_set,
            excluded_items_by_pack,
            excluded_items_by_type,
            kwargs.get("marketplace", ""),
        )
        id_set_creator.save_id_set()


# ====================== merge-id-sets ====================== #
@main.command(hidden=True)
@click.help_option("-h", "--help")
@click.option("-i1", "--id-set1", help="First id_set.json file path", required=True)
@click.option("-i2", "--id-set2", help="Second id_set.json file path", required=True)
@click.option("-o", "--output", help="File path of the united id_set", required=True)
@click.option(
    "-fd",
    "--fail-duplicates",
    help="Fails the process if any duplicates are found.",
    is_flag=True,
)
@click.pass_context
@logging_setup_decorator
def merge_id_sets(ctx, **kwargs):
    """Merge two id_sets"""
    from demisto_sdk.commands.common.update_id_set import merge_id_sets_from_files

    check_configuration_file("merge-id-sets", kwargs)
    first = kwargs["id_set1"]
    second = kwargs["id_set2"]
    output = kwargs["output"]
    fail_duplicates = kwargs["fail_duplicates"]

    _, duplicates = merge_id_sets_from_files(
        first_id_set_path=first, second_id_set_path=second, output_id_set_path=output
    )
    if duplicates:
        logger.info(
            f"[red]Failed to merge ID sets: {first} with {second}, "
            f"there are entities with ID: {duplicates} that exist in both ID sets"
        )
        if fail_duplicates:
            sys.exit(1)


# ====================== update-release-notes =================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    help="The relative path of the content pack. For example Packs/Pack_Name",
)
@click.option(
    "-u",
    "--update-type",
    help="The type of update being done. [major, minor, revision, documentation]",
    type=click.Choice(["major", "minor", "revision", "documentation"]),
)
@click.option(
    "-v", "--version", help="Bump to a specific version.", type=VersionParamType()
)
@click.option(
    "-g",
    "--use-git",
    help="Use git to identify the relevant changed files, will be used by default if '-i' is not set",
    is_flag=True,
)
@click.option(
    "-f",
    "--force",
    help="Force update release notes for a pack (even if not required).",
    is_flag=True,
)
@click.option(
    "--text",
    help="Text to add to all of the release notes files.",
)
@click.option(
    "--prev-ver", help="Previous branch or SHA1 commit to run checks against."
)
@click.option(
    "--pre_release",
    help="Indicates that this change should be designated a pre-release version.",
    is_flag=True,
)
@click.option(
    "-idp",
    "--id-set-path",
    help="The path of the id-set.json used for APIModule updates.",
    type=click.Path(resolve_path=True),
)
@click.option(
    "-bc",
    "--breaking-changes",
    help="If new version contains breaking changes.",
    is_flag=True,
)
@click.pass_context
@logging_setup_decorator
def update_release_notes(ctx, **kwargs):
    """Auto-increment pack version and generate release notes template."""
    from demisto_sdk.commands.update_release_notes.update_rn_manager import (
        UpdateReleaseNotesManager,
    )

    if is_sdk_defined_working_offline():
        logger.error(SDK_OFFLINE_ERROR_MESSAGE)
        sys.exit(1)

    check_configuration_file("update-release-notes", kwargs)
    if kwargs.get("force") and not kwargs.get("input"):
        logger.info(
            "[red]Please add a specific pack in order to force a release notes update."
        )
        sys.exit(0)

    if not kwargs.get("use_git") and not kwargs.get("input"):
        click.confirm(
            "No specific pack was given, do you want to update all changed packs?",
            abort=True,
        )

    try:
        rn_mng = UpdateReleaseNotesManager(
            user_input=kwargs.get("input"),
            update_type=kwargs.get("update_type"),
            pre_release=kwargs.get("pre_release", False),
            is_all=kwargs.get("use_git"),
            text=kwargs.get("text"),
            specific_version=kwargs.get("version"),
            id_set_path=kwargs.get("id_set_path"),
            prev_ver=kwargs.get("prev_ver"),
            is_force=kwargs.get("force", False),
            is_bc=kwargs.get("breaking_changes", False),
        )
        rn_mng.manage_rn_update()
        sys.exit(0)
    except Exception as e:
        logger.info(
            f"[red]An error occurred while updating the release notes: {str(e)}[/red]"
        )
        sys.exit(1)


# ====================== find-dependencies ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    help="Pack path to find dependencies. For example: Pack/HelloWorld. When using the"
    " --get-dependent-on flag, this argument can be used multiple times.",
    required=False,
    type=click.Path(exists=True, dir_okay=True),
    multiple=True,
)
@click.option(
    "-idp",
    "--id-set-path",
    help="Path to id set json file.",
    required=False,
    default="",
)
@click.option(
    "--no-update",
    help="Use to find the pack dependencies without updating the pack metadata.",
    required=False,
    is_flag=True,
)
@click.option(
    "--use-pack-metadata",
    help="Whether to update the dependencies from the pack metadata.",
    required=False,
    is_flag=True,
)
@click.option(
    "--all-packs-dependencies",
    help="Return a json file with ALL content packs dependencies. "
    "The json file will be saved under the path given in the "
    "'--output-path' argument",
    required=False,
    is_flag=True,
)
@click.option(
    "-o",
    "--output-path",
    help="The destination path for the packs dependencies json file. This argument is "
    "only relevant for when using the '--all-packs-dependecies' flag.",
    required=False,
)
@click.option(
    "--get-dependent-on",
    help="Get only the packs dependent ON the given pack. Note: this flag can not be"
    " used for the packs ApiModules and Base",
    required=False,
    is_flag=True,
)
@click.option(
    "-d",
    "--dependency",
    help="Find which items in a specific content pack appears as a mandatory "
    "dependency of the searched pack ",
    required=False,
)
@click.pass_context
@logging_setup_decorator
def find_dependencies(ctx, **kwargs):
    """Find pack dependencies and update pack metadata."""
    from demisto_sdk.commands.find_dependencies.find_dependencies import (
        PackDependencies,
    )

    check_configuration_file("find-dependencies", kwargs)
    update_pack_metadata = not kwargs.get("no_update")
    input_paths = kwargs.get("input")  # since it can be multiple, received as a tuple
    id_set_path = kwargs.get("id_set_path", "")
    use_pack_metadata = kwargs.get("use_pack_metadata", False)
    all_packs_dependencies = kwargs.get("all_packs_dependencies", False)
    get_dependent_on = kwargs.get("get_dependent_on", False)
    output_path = kwargs.get("output_path", ALL_PACKS_DEPENDENCIES_DEFAULT_PATH)
    dependency = kwargs.get("dependency", "")
    try:
        PackDependencies.find_dependencies_manager(
            id_set_path=str(id_set_path),
            update_pack_metadata=update_pack_metadata,
            use_pack_metadata=use_pack_metadata,
            input_paths=input_paths,
            all_packs_dependencies=all_packs_dependencies,
            get_dependent_on=get_dependent_on,
            output_path=output_path,
            dependency=dependency,
        )

    except ValueError as exp:
        logger.info(f"[red]{exp}[/red]")


# ====================== postman-codegen ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    help="The Postman collection 2.1 JSON file",
    required=True,
    type=click.File(),
)
@click.option(
    "-o",
    "--output",
    help="The output directory to save the config file or the integration",
    type=click.Path(dir_okay=True, exists=True),
    default=Path("."),
    show_default=True,
)
@click.option("-n", "--name", help="The output integration name")
@click.option(
    "-op",
    "--output-prefix",
    help="The global integration output prefix. By default it is the product name.",
)
@click.option(
    "-cp",
    "--command-prefix",
    help="The prefix for each command in the integration. By default is the product name in lower case",
)
@click.option(
    "--config-out",
    help="Used for advanced integration customisation. Generates a config json file instead of integration.",
    is_flag=True,
)
@click.option(
    "-p",
    "--package",
    help="Generated integration will be split to package format instead of a yml file.",
    is_flag=True,
)
@pass_config
@click.pass_context
@logging_setup_decorator
def postman_codegen(
    ctx,
    config,
    input: IO,
    output: Path,
    name: str,
    output_prefix: str,
    command_prefix: str,
    config_out: bool,
    package: bool,
    **kwargs,
):
    """Generates a Cortex XSOAR integration given a Postman collection 2.1 JSON file."""
    from demisto_sdk.commands.postman_codegen.postman_codegen import (
        postman_to_autogen_configuration,
    )
    from demisto_sdk.commands.split.ymlsplitter import YmlSplitter

    postman_config = postman_to_autogen_configuration(
        collection=json.load(input),
        name=name,
        command_prefix=command_prefix,
        context_path_prefix=output_prefix,
    )

    if config_out:
        path = Path(output) / f"config-{postman_config.name}.json"
        path.write_text(json.dumps(postman_config.to_dict(), indent=4))
        logger.info(f"Config file generated at:\n{str(path.absolute())}")
    else:
        # generate integration yml
        yml_path = postman_config.generate_integration_package(output, is_unified=True)
        if package:
            yml_splitter = YmlSplitter(
                configuration=config.configuration,
                file_type=FileType.INTEGRATION,
                input=str(yml_path),
                output=str(output),
            )
            yml_splitter.extract_to_package_format()
            logger.info(
                f"[green]Package generated at {str(Path(output).absolute())} successfully[/green]"
            )
        else:
            logger.info(
                f"[green]Integration generated at {str(yml_path.absolute())} successfully[/green]"
            )


# ====================== generate-integration ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    help="config json file produced by commands like postman-codegen and openapi-codegen",
    required=True,
    type=click.File(),
)
@click.option(
    "-o",
    "--output",
    help="The output directory to save the integration package",
    type=click.Path(dir_okay=True, exists=True),
    default=Path("."),
)
@click.pass_context
@logging_setup_decorator
def generate_integration(ctx, input: IO, output: Path, **kwargs):
    """Generates a Cortex XSOAR integration from a config json file,
    which is generated by commands like postman-codegen
    """
    from demisto_sdk.commands.generate_integration.code_generator import (
        IntegrationGeneratorConfig,
    )

    config_dict = json.load(input)
    config = IntegrationGeneratorConfig(**config_dict)

    config.generate_integration_package(output, True)


# ====================== openapi-codegen ====================== #
@main.command(
    short_help="""Generates a Cortex XSOAR integration given an OpenAPI specification file."""
)
@click.help_option("-h", "--help")
@click.option(
    "-i", "--input_file", help="The swagger file to load in JSON format", required=True
)
@click.option(
    "-cf",
    "--config_file",
    help="The integration configuration file. It is created in the first run of the command",
    required=False,
)
@click.option(
    "-n",
    "--base_name",
    help="The base filename to use for the generated files",
    required=False,
)
@click.option(
    "-o",
    "--output_dir",
    help="Directory to store the output in (default is current working directory)",
    required=False,
)
@click.option(
    "-pr",
    "--command_prefix",
    help="Add a prefix to each command in the code",
    required=False,
)
@click.option("-c", "--context_path", help="Context output path", required=False)
@click.option(
    "-u",
    "--unique_keys",
    help="Comma separated unique keys to use in context paths (case sensitive)",
    required=False,
)
@click.option(
    "-r",
    "--root_objects",
    help="Comma separated JSON root objects to use in command outputs (case sensitive)",
    required=False,
)
@click.option(
    "-f", "--fix_code", is_flag=True, help="Fix the python code using autopep8"
)
@click.option(
    "-a",
    "--use_default",
    is_flag=True,
    help="Use the automatically generated integration configuration"
    " (Skip the second run).",
)
@click.pass_context
@logging_setup_decorator
def openapi_codegen(ctx, **kwargs):
    """Generates a Cortex XSOAR integration given an OpenAPI specification file.
    In the first run of the command, an integration configuration file is created, which can be modified.
    Then, the command is run a second time with the integration configuration to generate the actual integration files.
    """
    from demisto_sdk.commands.openapi_codegen.openapi_codegen import OpenAPIIntegration

    check_configuration_file("openapi-codegen", kwargs)
    if not kwargs.get("output_dir"):
        output_dir = os.getcwd()
    else:
        output_dir = kwargs["output_dir"]

    # Check the directory exists and if not, try to create it
    if not Path(output_dir).exists():
        try:
            os.mkdir(output_dir)
        except Exception as err:
            logger.info(f"[red]Error creating directory {output_dir} - {err}[/red]")
            sys.exit(1)
    if not os.path.isdir(output_dir):
        logger.info(f'[red]The directory provided "{output_dir}" is not a directory')
        sys.exit(1)

    input_file = kwargs["input_file"]
    base_name = kwargs.get("base_name")
    if base_name is None:
        base_name = "GeneratedIntegration"

    command_prefix = kwargs.get("command_prefix")
    if command_prefix is None:
        command_prefix = "-".join(base_name.split(" ")).lower()

    context_path = kwargs.get("context_path")
    if context_path is None:
        context_path = base_name.replace(" ", "")

    unique_keys = kwargs.get("unique_keys", "")
    if unique_keys is None:
        unique_keys = ""

    root_objects = kwargs.get("root_objects", "")
    if root_objects is None:
        root_objects = ""

    fix_code = kwargs.get("fix_code", False)

    configuration = None
    if kwargs.get("config_file"):
        try:
            with open(kwargs["config_file"]) as config_file:
                configuration = json.load(config_file)
        except Exception as e:
            logger.info(f"[red]Failed to load configuration file: {e}[/red]")

    logger.info("Processing swagger file...")
    integration = OpenAPIIntegration(
        input_file,
        base_name,
        command_prefix,
        context_path,
        unique_keys=unique_keys,
        root_objects=root_objects,
        fix_code=fix_code,
        configuration=configuration,
    )

    integration.load_file()
    if not kwargs.get("config_file"):
        integration.save_config(integration.configuration, output_dir)
        logger.info(f"[green]Created configuration file in {output_dir}[/green]")
        if not kwargs.get("use_default", False):
            config_path = os.path.join(output_dir, f"{base_name}_config.json")
            command_to_run = (
                f'demisto-sdk openapi-codegen -i "{input_file}" -cf "{config_path}" -n "{base_name}" '
                f'-o "{output_dir}" -pr "{command_prefix}" -c "{context_path}"'
            )
            if unique_keys:
                command_to_run = command_to_run + f' -u "{unique_keys}"'
            if root_objects:
                command_to_run = command_to_run + f' -r "{root_objects}"'
            if (
                kwargs.get("console_log_threshold")
                and int(kwargs.get("console_log_threshold", logging.INFO))
                >= logging.DEBUG
            ):
                command_to_run = command_to_run + " -v"
            if fix_code:
                command_to_run = command_to_run + " -f"

            logger.info(
                f"Run the command again with the created configuration file(after a review): {command_to_run}"
            )
            sys.exit(0)

    if integration.save_package(output_dir):
        logger.info(
            f"Successfully finished generating integration code and saved it in {output_dir}",
            "green",
        )
    else:
        logger.info(
            f"[red]There was an error creating the package in {output_dir}[/red]"
        )
        sys.exit(1)


# ====================== test-content command ====================== #
@main.command(
    short_help="""Created incidents for selected test-playbooks and gives a report about the results""",
    hidden=True,
)
@click.help_option("-h", "--help")
@click.option(
    "-a",
    "--artifacts-path",
    help="Destination directory to create the artifacts.",
    type=click.Path(file_okay=False, resolve_path=True),
    default=Path("./Tests"),
    required=True,
)
@click.option(
    "-k", "--api-key", help="The Demisto API key for the server", required=True
)
@click.option("-s", "--server", help="The server URL to connect to")
@click.option("-c", "--conf", help="Path to content conf.json file", required=True)
@click.option("-e", "--secret", help="Path to content-test-conf conf.json file")
@click.option("-n", "--nightly", type=bool, help="Run nightly tests")
@click.option("-t", "--slack", help="The token for slack", required=True)
@click.option("-a", "--circleci", help="The token for circleci", required=True)
@click.option("-b", "--build-number", help="The build number", required=True)
@click.option(
    "-g", "--branch-name", help="The current content branch name", required=True
)
@click.option("-i", "--is-ami", type=bool, help="is AMI build or not", default=False)
@click.option(
    "-m",
    "--mem-check",
    type=bool,
    help="Should trigger memory checks or not. The slack channel to check the data is: "
    "dmst_content_nightly_memory_data",
    default=False,
)
@click.option(
    "-d",
    "--server-version",
    help="Which server version to run the tests on(Valid only when using AMI)",
    default="NonAMI",
)
@click.option(
    "-u",
    "--use-retries",
    is_flag=True,
    help="Should use retries mechanism or not (if test-playbook fails, it will execute it again few times and "
    "determine success according to most of the runs",
    default=False,
)
@click.option(
    "--server-type",
    help="On which server type runs the tests:XSIAM, XSOAR, XSOAR SAAS",
    default="XSOAR",
)
@click.option(
    "--product-type",
    help="On which product type runs the tests:XSIAM, XSOAR",
    default="XSOAR",
)
@click.option(
    "-x", "--xsiam-machine", help="XSIAM machine to use, if it is XSIAM build."
)
@click.option("--xsiam-servers-path", help="Path to secret xsiam server metadata file.")
@click.option(
    "--xsiam-servers-api-keys-path", help="Path to file with XSIAM Servers api keys."
)
@click.pass_context
@logging_setup_decorator
def test_content(ctx, **kwargs):
    """Configure instances for the integration needed to run tests_to_run tests.
    Run test module on each integration.
    create an investigation for each test.
    run test playbook on the created investigation using mock if possible.
    Collect the result and give a report.
    """
    from demisto_sdk.commands.test_content.execute_test_content import (
        execute_test_content,
    )

    check_configuration_file("test-content", kwargs)
    execute_test_content(**kwargs)


# ====================== doc-review ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-i", "--input", type=str, help="The path to the file to check", multiple=True
)
@click.option(
    "--no-camel-case",
    is_flag=True,
    help="Whether to check CamelCase words",
    default=False,
)
@click.option(
    "--known-words",
    type=str,
    help="The path to a file containing additional known words",
    multiple=True,
)
@click.option(
    "--always-true",
    is_flag=True,
    help="Whether to fail the command if misspelled words are found",
)
@click.option(
    "--expand-dictionary",
    is_flag=True,
    help="Whether to expand the base dictionary to include more words - "
    "will download 'brown' corpus from nltk package",
)
@click.option(
    "--templates", is_flag=True, help="Whether to print release notes templates"
)
@click.option(
    "-g",
    "--use-git",
    is_flag=True,
    help="Use git to identify the relevant changed files, "
    "will be used by default if '-i' and '--templates' are not set",
)
@click.option(
    "--prev-ver",
    type=str,
    help="The branch against which changes will be detected "
    "if '-g' flag is set. Default is 'demisto/master'",
)
@click.option(
    "-rn", "--release-notes", is_flag=True, help="Will run only on release notes files"
)
@click.option(
    "-xs",
    "--xsoar-only",
    is_flag=True,
    help="Run only on files from XSOAR-supported Packs.",
    default=False,
)
@click.option(
    "-pkw/-spkw",
    "--use-packs-known-words/--skip-packs-known-words",
    is_flag=True,
    help="Will find and load the known_words file from the pack. "
    "To use this option make sure you are running from the "
    "content directory.",
    default=True,
)
@click.pass_context
@logging_setup_decorator
def doc_review(ctx, **kwargs):
    """Check the spelling in .md and .yml files as well as review release notes"""
    from demisto_sdk.commands.doc_reviewer.doc_reviewer import DocReviewer

    doc_reviewer = DocReviewer(
        file_paths=kwargs.get("input", []),
        known_words_file_paths=kwargs.get("known_words", []),
        no_camel_case=kwargs.get("no_camel_case"),
        no_failure=kwargs.get("always_true"),
        expand_dictionary=kwargs.get("expand_dictionary"),
        templates=kwargs.get("templates"),
        use_git=kwargs.get("use_git"),
        prev_ver=kwargs.get("prev_ver"),
        release_notes_only=kwargs.get("release_notes"),
        xsoar_only=kwargs.get("xsoar_only"),
        load_known_words_from_pack=kwargs.get("use_packs_known_words"),
    )
    result = doc_reviewer.run_doc_review()
    if result:
        sys.exit(0)

    sys.exit(1)


# ====================== integration-diff ====================== #
@main.command(
    name="integration-diff",
    help="""Given two versions of an integration, Check that everything in the old integration is covered in
              the new integration""",
)
@click.help_option("-h", "--help")
@click.option(
    "-n",
    "--new",
    type=str,
    help="The path to the new version of the integration",
    required=True,
)
@click.option(
    "-o",
    "--old",
    type=str,
    help="The path to the old version of the integration",
    required=True,
)
@click.option(
    "--docs-format",
    is_flag=True,
    help="Whether output should be in the format for the version differences section in README.",
)
@click.pass_context
@logging_setup_decorator
def integration_diff(ctx, **kwargs):
    """
    Checks for differences between two versions of an integration, and verified that the new version covered the old version.
    """
    from demisto_sdk.commands.integration_diff.integration_diff_detector import (
        IntegrationDiffDetector,
    )

    integration_diff_detector = IntegrationDiffDetector(
        new=kwargs.get("new", ""),
        old=kwargs.get("old", ""),
        docs_format=kwargs.get("docs_format", False),
    )
    result = integration_diff_detector.check_different()

    if result:
        sys.exit(0)

    sys.exit(1)


# ====================== generate_yml_from_python ====================== #
@main.command(
    name="generate-yml-from-python",
    help="""Generate YML file from Python code that includes special syntax.\n
                      The output file name will be the same as the Python code with the `.yml` extension instead of `.py`.\n
                      The generation currently supports integrations only.\n
                      For more information on usage and installation visit the command's README.md file.""",
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    type=click.Path(exists=True),
    help="The path to the python code to generate from",
    required=True,
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    type=bool,
    help="Override existing yml file.",
    required=False,
)
@click.pass_context
@logging_setup_decorator
def generate_yml_from_python(ctx, **kwargs):
    """
    Checks for differences between two versions of an integration, and verified that the new version covered the old version.
    """
    from demisto_sdk.commands.generate_yml_from_python.generate_yml import YMLGenerator

    yml_generator = YMLGenerator(
        filename=kwargs.get("input", ""),
        force=kwargs.get("force", False),
    )
    yml_generator.generate()
    yml_generator.save_to_yml_file()


# ====================== convert ====================== #
@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    type=click.Path(exists=True),
    required=True,
    help="The path of the content pack/directory/file to convert.",
)
@click.option(
    "-v", "--version", required=True, help="Version the input to be compatible with."
)
@pass_config
@click.pass_context
@logging_setup_decorator
def convert(ctx, config, **kwargs):
    """
    Convert the content of the pack/directory in the given input to be compatible with the version given by
    version command.
    """
    from demisto_sdk.commands.convert.convert_manager import ConvertManager

    check_configuration_file("convert", kwargs)
    sys.path.append(config.configuration.env_dir)

    input_path = kwargs["input"]
    server_version = kwargs["version"]
    convert_manager = ConvertManager(input_path, server_version)
    result = convert_manager.convert()

    if result:
        sys.exit(1)

    sys.exit(0)


# ====================== generate-unit-tests ====================== #


@main.command(short_help="""Generates unit tests for integration code.""")
@click.help_option("-h", "--help")
@click.option(
    "-c",
    "--commands",
    help="Specific commands name to generate unit test for (e.g. xdr-get-incidents)",
    required=False,
)
@click.option(
    "-o",
    "--output_dir",
    help="Directory to store the output in (default is the input integration directory)",
    required=False,
)
@click.option("-i", "--input_path", help="Valid integration file path.", required=True)
@click.option(
    "-d", "--use_demisto", help="Run commands at Demisto automatically.", is_flag=True
)
@click.option("--insecure", help="Skip certificate validation", is_flag=True)
@click.option(
    "-e",
    "--examples",
    help="Integrations: path for file containing command examples."
    " Each command should be in a separate line.",
)
@click.option(
    "-a",
    "--append",
    help="Append generated test file to the existing <integration_name>_test.py. Else, overwriting existing UT",
    is_flag=True,
)
@click.pass_context
@logging_setup_decorator
def generate_unit_tests(
    ctx,
    input_path: str = "",
    commands: list = [],
    output_dir: str = "",
    examples: str = "",
    insecure: bool = False,
    use_demisto: bool = False,
    append: bool = False,
    **kwargs,
):
    """
    This command is used to generate unit tests automatically from an  integration python code.
    Also supports generating unit tests for specific commands.
    """
    logging.getLogger("PYSCA").propagate = False
    from demisto_sdk.commands.generate_unit_tests.generate_unit_tests import (
        run_generate_unit_tests,
    )

    return run_generate_unit_tests(
        input_path, commands, output_dir, examples, insecure, use_demisto, append
    )


@main.command(
    name="error-code",
    help="Quickly find relevant information regarding an error code.",
)
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    required=True,
    help="The error code to search for.",
)
@pass_config
@click.pass_context
@logging_setup_decorator
def error_code(ctx, config, **kwargs):
    from demisto_sdk.commands.error_code_info.error_code_info import (
        generate_error_code_information,
    )

    check_configuration_file("error-code-info", kwargs)
    sys.path.append(config.configuration.env_dir)

    result = generate_error_code_information(kwargs.get("input"))

    sys.exit(result)


# ====================== create-content-graph ====================== #
@main.command(
    hidden=True,
)
@click.help_option("-h", "--help")
@click.option(
    "-o",
    "--output-path",
    type=click.Path(resolve_path=True, path_type=Path, dir_okay=True, file_okay=False),
    default=None,
    help="Output folder to place the zip file of the graph exported CSVs files",
)
@click.option(
    "-mp",
    "--marketplace",
    help="The marketplace to generate the graph for.",
    default="xsoar",
    type=click.Choice(list(MarketplaceVersions)),
)
@click.option(
    "-nd",
    "--no-dependencies",
    is_flag=True,
    help="Whether or not to include dependencies.",
    default=False,
)
@click.pass_context
@logging_setup_decorator
def create_content_graph(
    ctx,
    marketplace: str = MarketplaceVersions.XSOAR,
    no_dependencies: bool = False,
    output_path: Path = None,
    **kwargs,
):
    logger.warning(
        "[WARNING] The 'create-content-graph' command is deprecated and will be removed "
        "in upcoming versions. Use 'demisto-sdk graph create' instead."
    )
    ctx.invoke(
        create,
        ctx,
        marketplace=marketplace,
        no_dependencies=no_dependencies,
        output_path=output_path,
        **kwargs,
    )


# ====================== update-content-graph ====================== #
@main.command(
    hidden=True,
)
@click.help_option("-h", "--help")
@click.option(
    "-mp",
    "--marketplace",
    help="The marketplace the artifacts are created for, that "
    "determines which artifacts are created for each pack. "
    "Default is the XSOAR marketplace, that has all of the packs "
    "artifacts.",
    default="xsoar",
    type=click.Choice(list(MarketplaceVersions)),
)
@click.option(
    "-g",
    "--use-git",
    is_flag=True,
    show_default=True,
    default=False,
    help="Whether to use git to determine the packs to update",
)
@click.option(
    "-i",
    "--imported-path",
    type=click.Path(
        path_type=Path, resolve_path=True, exists=True, file_okay=True, dir_okay=False
    ),
    default=None,
    help="Path to content graph zip file to import",
)
@click.option(
    "-p",
    "--packs",
    help="A comma-separated list of packs to update",
    multiple=True,
    default=None,
)
@click.option(
    "-nd",
    "--no-dependencies",
    is_flag=True,
    help="Whether dependencies should be included in the graph",
    default=False,
)
@click.option(
    "-o",
    "--output-path",
    type=click.Path(resolve_path=True, path_type=Path, dir_okay=True, file_okay=False),
    default=None,
    help="Output folder to place the zip file of the graph exported CSVs files",
)
@click.pass_context
@logging_setup_decorator
def update_content_graph(
    ctx,
    use_git: bool = False,
    marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    imported_path: Path = None,
    packs: list = None,
    no_dependencies: bool = False,
    output_path: Path = None,
    **kwargs,
):
    logger.warning(
        "[WARNING] The 'update-content-graph' command is deprecated and will be removed "
        "in upcoming versions. Use 'demisto-sdk graph update' instead."
    )
    ctx.invoke(
        update,
        ctx,
        use_git=use_git,
        marketplace=marketplace,
        imported_path=imported_path,
        packs_to_update=packs,
        no_dependencies=no_dependencies,
        output_path=output_path,
        **kwargs,
    )


@main.command(short_help="Setup integration environments")
@click.option(
    "--ide",
    help="IDE type to configure the environment for. If not specified, the IDE will be auto-detected. Case-insensitive.",
    default="auto-detect",
    type=click.Choice(
        ["auto-detect"] + [IDEType.value for IDEType in IDEType], case_sensitive=False
    ),
)
@click.option(
    "-i",
    "--input",
    type=PathsParamType(
        exists=True, resolve_path=True
    ),  # PathsParamType allows passing a list of paths
    help="A list of content packs/files to validate.",
)
@click.option(
    "--create-virtualenv",
    is_flag=True,
    default=False,
    help="Create a virtualenv for the environment.",
)
@click.option(
    "--overwrite-virtualenv",
    is_flag=True,
    default=False,
    help="Overwrite existing virtualenvs. Relevant only if the 'create-virtualenv' flag is used.",
)
@click.option(
    "--secret-id",
    help="Secret ID to use for the Google Secret Manager instance. Requires the `DEMISTO_SDK_GCP_PROJECT_ID` environment variable to be set.",
    required=False,
)
@click.option(
    "--instance-name",
    required=False,
    help="Instance name to configure in XSOAR / XSIAM.",
)
@click.option(
    "--run-test-module",
    required=False,
    is_flag=True,
    default=False,
    help="Whether to run test-module on the configured XSOAR / XSIAM instance.",
)
@click.option(
    "--clean",
    is_flag=True,
    default=False,
    help="Clean the repository of temporary files created by the 'lint' command.",
)
@click.argument("file_paths", nargs=-1, type=click.Path(exists=True, resolve_path=True))
def setup_env(
    input,
    ide,
    file_paths,
    create_virtualenv,
    overwrite_virtualenv,
    secret_id,
    instance_name,
    run_test_module,
    clean,
):
    from demisto_sdk.commands.setup_env.setup_environment import (
        setup_env,
    )

    if ide == "auto-detect":
        # Order decides which IDEType will be selected for configuration if multiple IDEs are detected
        if (CONTENT_PATH / ".vscode").exists():
            logger.info(
                "Visual Studio Code IDEType has been detected and will be configured."
            )
            ide_type = IDEType.VSCODE
        elif (CONTENT_PATH / ".idea").exists():
            logger.info(
                "PyCharm / IDEA IDEType has been detected and will be configured."
            )
            ide_type = IDEType.PYCHARM
        else:
            raise RuntimeError(
                "Could not detect IDEType. Please select a specific IDEType using the --ide flag."
            )

    else:
        ide_type = IDEType(ide)

    if input:
        file_paths = tuple(input.split(","))

    setup_env(
        file_paths=file_paths,
        ide_type=ide_type,
        create_virtualenv=create_virtualenv,
        overwrite_virtualenv=overwrite_virtualenv,
        secret_id=secret_id,
        instance_name=instance_name,
        test_module=run_test_module,
        clean=clean,
    )


@main.result_callback()
def exit_from_program(result=0, **kwargs):
    sys.exit(result)


# ====================== Pre-Commit ====================== #
pre_commit_app = typer.Typer(name="Pre-Commit")


@pre_commit_app.command()
def pre_commit(
    input_files: Optional[List[Path]] = typer.Option(
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
        False, "--staged-only", help="Whether to run only on staged files"
    ),
    commited_only: bool = typer.Option(
        False, "--commited-only", help="Whether to run on commited files only"
    ),
    git_diff: bool = typer.Option(
        False,
        "--git-diff",
        "-g",
        help="Whether to use git to determine which files to run on",
    ),
    all_files: bool = typer.Option(
        False, "--all-files", "-a", help="Whether to run on all files"
    ),
    mode: str = typer.Option(
        "", "--mode", help="Special mode to run the pre-commit with"
    ),
    skip: Optional[List[str]] = typer.Option(
        None, "--skip", help="A list of precommit hooks to skip"
    ),
    validate: bool = typer.Option(
        True, "--validate/--no-validate", help="Whether to run demisto-sdk validate"
    ),
    format: bool = typer.Option(
        False, "--format/--no-format", help="Whether to run demisto-sdk format"
    ),
    secrets: bool = typer.Option(
        True, "--secrets/--no-secrets", help="Whether to run demisto-sdk secrets"
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Verbose output of pre-commit"
    ),
    show_diff_on_failure: bool = typer.Option(
        False, "--show-diff-on-failure", help="Show diff on failure"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Whether to run the pre-commit hooks in dry-run mode, which will only create the config file",
    ),
    docker: bool = typer.Option(
        True, "--docker/--no-docker", help="Whether to run docker based hooks or not."
    ),
    run_hook: Optional[str] = typer.Argument(None, help="A specific hook to run"),
    console_log_threshold: str = typer.Option(
        "INFO",
        "--console-log-threshold",
        help="Minimum logging threshold for the console logger.",
    ),
    file_log_threshold: str = typer.Option(
        "DEBUG",
        "--file-log-threshold",
        help="Minimum logging threshold for the file logger.",
    ),
    log_file_path: Optional[str] = typer.Option(
        None,
        "--log-file-path",
        help="Path to save log files onto.",
    ),
):
    logging_setup(
        console_log_threshold=console_log_threshold,
        file_log_threshold=file_log_threshold,
        log_file_path=log_file_path,
    )

    from demisto_sdk.commands.pre_commit.pre_commit_command import pre_commit_manager

    return_code = pre_commit_manager(
        input_files,
        staged_only,
        commited_only,
        git_diff,
        all_files,
        mode,
        skip,
        validate,
        format,
        secrets,
        verbose,
        show_diff_on_failure,
        run_docker_hooks=docker,
        dry_run=dry_run,
        run_hook=run_hook,
    )
    if return_code:
        raise typer.Exit(1)


main.add_command(typer.main.get_command(pre_commit_app), "pre-commit")


# ====================== modeling-rules command group ====================== #
modeling_rules_app = typer.Typer(
    name="modeling-rules", hidden=True, no_args_is_help=True
)
modeling_rules_app.command("test", no_args_is_help=True)(
    test_modeling_rule.test_modeling_rule
)
modeling_rules_app.command("init-test-data", no_args_is_help=True)(
    init_test_data.init_test_data
)
typer_click_object = typer.main.get_command(modeling_rules_app)
main.add_command(typer_click_object, "modeling-rules")

app_generate_modeling_rules = typer.Typer(
    name="generate-modeling-rules", no_args_is_help=True
)
app_generate_modeling_rules.command("generate-modeling-rules", no_args_is_help=True)(
    generate_modeling_rules.generate_modeling_rules
)

typer_click_object2 = typer.main.get_command(app_generate_modeling_rules)
main.add_command(typer_click_object2, "generate-modeling-rules")


# ====================== graph command group ====================== #

graph_cmd_group = typer.Typer(name="graph", hidden=True, no_args_is_help=True)
graph_cmd_group.command("create", no_args_is_help=False)(create)
graph_cmd_group.command("update", no_args_is_help=False)(update)
graph_cmd_group.command("get-relationships", no_args_is_help=True)(get_relationships)
graph_cmd_group.command("get-dependencies", no_args_is_help=True)(get_dependencies)
main.add_command(typer.main.get_command(graph_cmd_group), "graph")


# ====================== Xsoar-Lint ====================== #

xsoar_linter_app = typer.Typer(name="Xsoar-Lint")


@xsoar_linter_app.command(
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def xsoar_linter(
    file_paths: Optional[List[Path]] = typer.Argument(
        None,
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help=("The paths to run xsoar linter on. May pass multiple paths."),
    )
):
    """
    Runs the xsoar lint on the given paths.
    """
    return_code = xsoar_linter_manager(
        file_paths,
    )
    if return_code:
        raise typer.Exit(1)


main.add_command(typer.main.get_command(xsoar_linter_app), "xsoar-lint")


if __name__ == "__main__":
    main()
