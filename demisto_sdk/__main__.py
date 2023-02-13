# Site packages
import copy
import logging
import os
import sys
from pathlib import Path
from typing import IO, Any, Dict

import click
import git
import typer
from pkg_resources import DistributionNotFound, get_distribution

from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    ENV_DEMISTO_SDK_MARKETPLACE,
    FileType,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content_constant_paths import (
    ALL_PACKS_DEPENDENCIES_DEFAULT_PATH,
)
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import (
    find_type,
    get_last_remote_release_version,
    get_release_note_entries,
    is_external_repository,
    print_error,
    print_success,
    print_warning,
)
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface,
)
from demisto_sdk.commands.prepare_content.prepare_upload_manager import (
    PrepareUploadManager,
)
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter
from demisto_sdk.commands.test_content.test_modeling_rule import (
    init_test_data,
    test_modeling_rule,
)
from demisto_sdk.commands.upload.upload import upload_content_entity
from demisto_sdk.utils.utils import check_configuration_file

json = JSON_Handler()

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


json = JSON_Handler()


class DemistoSDK:
    """
    The core class for the SDK.
    """

    def __init__(self):
        self.configuration = None


pass_config = click.make_pass_decorator(DemistoSDK, ensure=True)


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
def main(config, version, release_notes):
    config.configuration = Configuration()
    import dotenv

    from demisto_sdk.commands.common.tools import get_content_path

    dotenv.load_dotenv(Path(get_content_path()) / ".env", override=True)  # type: ignore # load .env file from the cwd
    if (
        not os.getenv("DEMISTO_SDK_SKIP_VERSION_CHECK") or version
    ):  # If the key exists/called to version
        try:
            __version__ = get_distribution("demisto-sdk").version
        except DistributionNotFound:
            __version__ = "dev"
            print_warning(
                "Cound not find the version of the demisto-sdk. This usually happens when running in a development environment."
            )
        else:
            last_release = get_last_remote_release_version()
            print_warning(f"You are using demisto-sdk {__version__}.")
            if last_release and __version__ != last_release:
                print_warning(
                    f"however version {last_release} is available.\n"
                    f"To update, run pip3 install --upgrade demisto-sdk"
                )
            if release_notes:
                rn_entries = get_release_note_entries(__version__)

                if not rn_entries:
                    print_warning("\nCould not get the release notes for this version.")
                else:
                    click.echo(
                        "\nThe following are the release note entries for the current version:\n"
                    )
                    for rn in rn_entries:
                        click.echo(rn)
                    click.echo("")


# ====================== split ====================== #
@main.command()
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
def split(config, **kwargs):
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
    ]:
        print_error(
            "File is not an Integration, Script, Generic Module, Modeling Rule or Parsing Rule."
        )
        return 1

    if file_type in [
        FileType.INTEGRATION,
        FileType.SCRIPT,
        FileType.MODELING_RULE,
        FileType.PARSING_RULE,
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
            no_logging=kwargs.get("no_logging"),  # type: ignore[arg-type]
            new_module_file=kwargs.get("new_module_file"),  # type: ignore[arg-type]
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
def extract_code(config, **kwargs):
    """Extract code from a Demisto integration or script yaml file."""
    from demisto_sdk.commands.split.ymlsplitter import YmlSplitter

    check_configuration_file("extract-code", kwargs)
    file_type: FileType = find_type(kwargs.get("input", ""), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT]:
        print_error("File is not an Integration or Script.")
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
    help="The directory path to the files or path to the file to unify",
    required=True,
    type=click.Path(dir_okay=True),
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
    type=click.Choice(["xsoar", "marketplacev2", "v2"]),
)
@click.option(
    "-v",
    "--verbose",
    help="Verbose output - mainly for debugging purposes",
    is_flag=True,
)
def prepare_content(**kwargs):
    """
    This command is used to prepare the content to be used in the platform.


    """
    from demisto_sdk.commands.common.logger import logging_setup

    if kwargs.get("verbose"):
        logging_setup(3)
    if click.get_current_context().info_name == "unify":
        kwargs["unify_only"] = True

    check_configuration_file("unify", kwargs)
    # Input is of type Path.
    kwargs["input"] = str(kwargs["input"])
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


@main.command()
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
def zip_packs(**kwargs) -> int:
    """Generating zipped packs that are ready to be uploaded to Cortex XSOAR machine."""
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.upload.uploader import Uploader
    from demisto_sdk.commands.zip_packs.packs_zipper import (
        EX_FAIL,
        EX_SUCCESS,
        PacksZipper,
    )

    logging_setup(3)
    check_configuration_file("zip-packs", kwargs)

    # if upload is true - all zip packs will be compressed to one zip file
    should_upload = kwargs.pop("upload", False)
    zip_all = kwargs.pop("zip_all", False) or should_upload

    if marketplace := kwargs.get("marketplace"):
        os.environ[ENV_DEMISTO_SDK_MARKETPLACE] = marketplace.lower()

    packs_zipper = PacksZipper(
        zip_all=zip_all, pack_paths=kwargs.pop("input"), quiet_mode=zip_all, **kwargs
    )
    zip_path, unified_pack_names = packs_zipper.zip_packs()

    if should_upload and zip_path:
        return Uploader(input=zip_path, pack_names=unified_pack_names).upload()

    return EX_SUCCESS if zip_path is not None else EX_FAIL


# ====================== validate ====================== #
@main.command()
@click.help_option("-h", "--help")
@click.option(
    "--no-conf-json",
    is_flag=True,
    default=False,
    show_default=True,
    help="Skip conf.json validation.",
)
@click.option(
    "-s",
    "--id-set",
    is_flag=True,
    default=False,
    show_default=True,
    help="Perform validations using the id_set file.",
)
@click.option(
    "-idp",
    "--id-set-path",
    help="The path of the id-set.json used for validations.",
    type=click.Path(resolve_path=True),
)
@click.option(
    "-gr",
    "--graph",
    is_flag=True,
    default=False,
    show_default=True,
    help="Perform validations on content graph.",
)
@click.option(
    "--prev-ver", help="Previous branch or SHA1 commit to run checks against."
)
@click.option(
    "--no-backward-comp",
    is_flag=True,
    show_default=True,
    help="Whether to check backward compatibility or not.",
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
    help="Whether to include untracked files in the validation. "
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
    type=click.Path(exists=True, resolve_path=True),
    help="The path of the content pack/file to validate specifically.",
)
@click.option(
    "--skip-pack-release-notes",
    is_flag=True,
    help="Skip validation of pack release notes.",
)
@click.option(
    "--print-ignored-errors", is_flag=True, help="Print ignored errors as warnings."
)
@click.option(
    "--print-ignored-files",
    is_flag=True,
    help="Print which files were ignored by the command.",
)
@click.option(
    "--no-docker-checks", is_flag=True, help="Whether to run docker image validation."
)
@click.option(
    "--silence-init-prints",
    is_flag=True,
    help="Whether to skip the initialization prints.",
)
@click.option(
    "--skip-pack-dependencies",
    is_flag=True,
    help="Skip validation of pack dependencies.",
)
@click.option(
    "--create-id-set", is_flag=True, help="Whether to create the id_set.json file."
)
@click.option(
    "-j",
    "--json-file",
    help="The JSON file path to which to output the command results.",
)
@click.option(
    "--skip-schema-check", is_flag=True, help="Whether to skip the file schema check."
)
@click.option(
    "--debug-git", is_flag=True, help="Whether to print debug logs for git statuses."
)
@click.option(
    "--print-pykwalify", is_flag=True, help="Whether to print the pykwalify log errors."
)
@click.option(
    "--quiet-bc-validation",
    help="Set backwards compatibility validation's errors as warnings.",
    is_flag=True,
)
@click.option(
    "--allow-skipped",
    help="Don't fail on skipped integrations or when all test playbooks are skipped.",
    is_flag=True,
)
@click.option(
    "--no-multiprocessing",
    help="run validate all without multiprocessing, for debugging purposes.",
    is_flag=True,
    default=False,
)
@click.option(
    "-sv",
    "--run-specific-validations",
    help="Run specific validations by stating the error codes.",
    is_flag=False,
)
@pass_config
def validate(config, **kwargs):
    """Validate your content files. If no additional flags are given, will validated only committed files."""
    from demisto_sdk.commands.validate.validate_manager import ValidateManager

    run_with_mp = not kwargs.pop("no_multiprocessing")
    check_configuration_file("validate", kwargs)
    sys.path.append(config.configuration.env_dir)

    file_path = kwargs["input"]

    if kwargs["post_commit"] and kwargs["staged"]:
        print_error("Could not supply the staged flag with the post-commit flag")
        sys.exit(1)
    try:
        is_external_repo = is_external_repository()
        # default validate to -g --post-commit
        if not kwargs.get("validate_all") and not kwargs["use_git"] and not file_path:
            kwargs["use_git"] = True
            kwargs["post_commit"] = True
        validator = ValidateManager(
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
        return validator.run_validation()
    except (git.InvalidGitRepositoryError, git.NoSuchPathError, FileNotFoundError) as e:
        print_error(e)
        print_error(
            "\nYou may not be running `demisto-sdk validate` command in the content directory.\n"
            "Please run the command from content directory"
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
def create_content_artifacts(**kwargs) -> int:
    """Generating the following artifacts:
    1. content_new - Contains all content objects of type json,yaml (from_version < 6.0.0)
    2. content_packs - Contains all packs from Packs - Ignoring internal files (to_version >= 6.0.0).
    3. content_test - Contains all test scripts/playbooks (from_version < 6.0.0)
    4. content_all - Contains all from content_new and content_test.
    5. uploadable_packs - Contains zipped packs that are ready to be uploaded to Cortex XSOAR machine.
    """
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
        ArtifactsManager,
    )

    logging_setup(3)
    check_configuration_file("create-content-artifacts", kwargs)
    if marketplace := kwargs.get("marketplace"):
        os.environ[ENV_DEMISTO_SDK_MARKETPLACE] = marketplace.lower()
    artifacts_conf = ArtifactsManager(**kwargs)
    return artifacts_conf.create_content_artifacts()


# ====================== secrets ====================== #
@main.command()
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
@pass_config
def secrets(config, **kwargs):
    """Run Secrets validator to catch sensitive data before exposing your code to public repository.
    Attach path to whitelist to allow manual whitelists.
    """
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
@main.command()
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
    "-v",
    "--verbose",
    count=True,
    help="Verbosity level -v / -vv / .. / -vvv",
    type=click.IntRange(0, 3, clamp=True),
    default=2,
    show_default=True,
)
@click.option(
    "-q", "--quiet", is_flag=True, help="Quiet output, only output results in the end"
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
    default="master",
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
    "-lp",
    "--log-path",
    help="Path to store all levels of logs",
    type=click.Path(resolve_path=True),
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
    help="The docker image to check package on. Possible values: 'native:maintenance', 'native:ga', 'native:dev',"
    " 'all', a specific docker image from Docker Hub (e.g devdemisto/python3:3.10.9.12345) or the default"
    " 'from-yml'.",
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
def lint(**kwargs):
    """Lint command will perform:
    1. Package in host checks - flake8, bandit, mypy, vulture.
    2. Package in docker image checks -  pylint, pytest, powershell - test, powershell - analyze.
    Meant to be used with integrations/scripts that use the folder (package) structure.
    Will lookup up what docker image to use and will setup the dev dependencies and file in the target folder.
    If no additional flags specifying the packs are given, will lint only changed files.
    """
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.lint.lint_manager import LintManager

    logging_setup(
        verbose=kwargs.get("verbose"),  # type: ignore[arg-type]
        quiet=kwargs.get("quiet"),  # type: ignore[arg-type]
        log_path=kwargs.get("log_path"),
    )  # type: ignore[arg-type]

    check_configuration_file("lint", kwargs)
    lint_manager = LintManager(
        input=kwargs.get("input"),  # type: ignore[arg-type]
        git=kwargs.get("git"),  # type: ignore[arg-type]
        all_packs=kwargs.get("all_packs"),  # type: ignore[arg-type]
        verbose=kwargs.get("verbose"),  # type: ignore[arg-type]
        quiet=kwargs.get("quiet"),  # type: ignore[arg-type]
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
        time_measurements_dir=kwargs.get("time_measurements_dir"),  # type: ignore[arg-type]
    )


# ====================== coverage-analyze ====================== #
@main.command()
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    help="The .coverage file to analyze.",
    default=os.path.join("coverage_report", ".coverage"),
    type=PathsParamType(exists=True, resolve_path=True),
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
    default="https://storage.googleapis.com/marketplace-dist-dev/code-coverage-reports/coverage-min.json",
    type=str,
)
def coverage_analyze(**kwargs):
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
    except Exception as error:
        logging.getLogger("demisto-sdk").error(error)

    return 1


# ====================== format ====================== #
@main.command()
@click.help_option("-h", "--help")
@click.option(
    "-i",
    "--input",
    help="The path of the script yml file\n"
    "If no input is specified, the format will be executed on all new/changed files.",
    type=click.Path(exists=True, resolve_path=True),
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
@click.option("-v", "--verbose", help="Verbose output", is_flag=True)
@click.option(
    "-y",
    "--assume-yes",
    help="Automatic yes to prompts; assume 'yes' as answer to all prompts and run non-interactively",
    is_flag=True,
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
    help="The path of the id_set json file.",
    type=click.Path(exists=True, resolve_path=True),
)
def format(
    input: Path,
    output: Path,
    from_version: str,
    no_validate: bool,
    update_docker: bool,
    verbose: bool,
    assume_yes: bool,
    deprecate: bool,
    use_git: bool,
    prev_ver: str,
    include_untracked: bool,
    add_tests: bool,
    id_set_path: str,
):
    """Run formatter on a given script/playbook/integration/incidentfield/indicatorfield/
    incidenttype/indicatortype/layout/dashboard/classifier/mapper/widget/report file/genericfield/generictype/
    genericmodule/genericdefinition.
    """
    from demisto_sdk.commands.format.format_module import format_manager

    return format_manager(
        str(input) if input else None,
        str(output) if output else None,
        from_version=from_version,
        no_validate=no_validate,
        update_docker=update_docker,
        assume_yes=assume_yes,
        verbose=verbose,
        deprecate=deprecate,
        use_git=use_git,
        prev_ver=prev_ver,
        include_untracked=include_untracked,
        add_tests=add_tests,
        id_set_path=id_set_path,
    )


# ====================== upload ====================== #
@main.command()
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
    "-z",
    "--zip",
    help="Compress the pack to zip before upload, this flag is relevant only for packs.",
    is_flag=True,
)
@click.option(
    "-x",
    "--xsiam",
    help="Upload the pack to XSIAM server. Must be used together with -z",
    is_flag=True,
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
@click.option("-v", "--verbose", help="Verbose output", is_flag=True)
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
    help="If true will skip override confirmation prompt while uploading packs.",
)
def upload(**kwargs):
    """Upload integration or pack to Demisto instance.
    DEMISTO_BASE_URL environment variable should contain the Demisto server base URL.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    * Note: Uploading classifiers to Cortex XSOAR is available from version 6.0.0 and up. *
    """
    return upload_content_entity(**kwargs)


# ====================== download ====================== #


@main.command()
@click.help_option("-h", "--help")
@click.option(
    "-o",
    "--output",
    help="The path of a package directory to download custom content to",
    required=False,
    multiple=False,
)
@click.option(
    "-i",
    "--input",
    help="Custom content file name to be downloaded. Can be provided multiple times",
    required=False,
    multiple=True,
)
@click.option(
    "-r",
    "--regex",
    help="Regex Pattern, download all the custom content files that match this regex pattern.",
    required=False,
)
@click.option("--insecure", help="Skip certificate validation", is_flag=True)
@click.option("-v", "--verbose", help="Verbose output", is_flag=True)
@click.option(
    "-f", "--force", help="Whether to override existing files or not", is_flag=True
)
@click.option(
    "-lf",
    "--list-files",
    help="Prints a list of all custom content files available to be downloaded",
    is_flag=True,
)
@click.option(
    "-a",
    "--all-custom-content",
    help="Download all available custom content files",
    is_flag=True,
)
@click.option(
    "-fmt",
    "--run-format",
    help="Whether to run demisto-sdk format on downloaded files or not",
    is_flag=True,
)
@click.option("--system", help="Download system items", is_flag=True, default=False)
@click.option(
    "-it",
    "--item-type",
    help="The items type to download, use just when downloading system items, should be one "
    "form the following list: [IncidentType, IndicatorType, Field, Layout, Playbook, "
    "Automation, Classifier, Mapper]",
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
def download(**kwargs):
    """Download custom content from Demisto instance.
    DEMISTO_BASE_URL environment variable should contain the Demisto server base URL.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    """
    from demisto_sdk.commands.download.downloader import Downloader

    check_configuration_file("download", kwargs)
    downloader: Downloader = Downloader(**kwargs)
    return downloader.download()


# ====================== update-xsoar-config-file ====================== #
@main.command()
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
def xsoar_config_file_update(**kwargs):
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
@main.command()
@click.help_option("-h", "--help")
@click.option("-q", "--query", help="The query to run", required=True)
@click.option("--insecure", help="Skip certificate validation", is_flag=True)
@click.option("-v", "--verbose", help="Verbose output", is_flag=True)
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
def run(**kwargs):
    """Run integration command on remote Demisto instance in the playground.
    DEMISTO_BASE_URL environment variable should contain the Demisto base URL.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    """
    from demisto_sdk.commands.run_cmd.runner import Runner

    check_configuration_file("run", kwargs)
    runner = Runner(**kwargs)
    return runner.run()


# ====================== run-playbook ====================== #
@main.command()
@click.help_option("-h", "--help")
@click.option(
    "--url",
    "-u",
    help="URL to a Demisto instance. You can also specify the URL as an environment variable named: DEMISTO_BASE_URL",
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
    help="Timeout for the command. The playbook will continue to run in Demisto",
)
@click.option("--insecure", help="Skip certificate validation.", is_flag=True)
def run_playbook(**kwargs):
    """Run a playbook in Demisto.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    Example: DEMISTO_API_KEY=<API KEY> demisto-sdk run-playbook -p 'p_name' -u
    'https://demisto.local'.
    """
    from demisto_sdk.commands.run_playbook.playbook_runner import PlaybookRunner

    check_configuration_file("run-playbook", kwargs)
    playbook_runner = PlaybookRunner(**kwargs)
    return playbook_runner.run_playbook()


# ====================== run-test-playbook ====================== #
@main.command()
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
def run_test_playbook(**kwargs):
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
    "-v",
    "--verbose",
    is_flag=True,
    help="Verbose output - mainly for debugging purposes",
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
def generate_outputs(**kwargs):
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
@main.command()
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
    "-v",
    "--verbose",
    help="Verbose output for debug purposes - shows full exception stack trace",
    is_flag=True,
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
def generate_test_playbook(**kwargs):
    """Generate test playbook from integration or script"""
    from demisto_sdk.commands.generate_test_playbook.test_playbook_generator import (
        PlaybookTestsGenerator,
    )

    check_configuration_file("generate-test-playbook", kwargs)
    file_type: FileType = find_type(kwargs.get("input", ""), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT]:
        print_error(
            "Generating test playbook is possible only for an Integration or a Script."
        )
        return 1

    try:
        generator = PlaybookTestsGenerator(file_type=file_type.value, **kwargs)
        if generator.run():
            sys.exit(0)
        sys.exit(1)
    except PlaybookTestsGenerator.InvalidOutputPathError as e:
        print_error(str(e))
        return 1


# ====================== init ====================== #


@main.command()
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
def init(**kwargs):
    """Initialize a new Pack, Integration or Script.
    If the script/integration flags are not present, we will create a pack with the given name.
    Otherwise when using the flags we will generate a script/integration based on your selection.
    """
    from demisto_sdk.commands.init.initiator import Initiator

    check_configuration_file("init", kwargs)
    initiator = Initiator(**kwargs)
    initiator.init()
    return 0


# ====================== generate-docs ====================== #
@main.command()
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
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Verbose output - mainly for debugging purposes.",
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
def generate_docs(**kwargs):
    """Generate documentation for integration, playbook or script from yaml file."""

    check_configuration_file("generate-docs", kwargs)
    input_path_str: str = kwargs.get("input", "")
    if not (input_path := Path(input_path_str)).exists():
        print_error(f"input {input_path_str} does not exist")
        return 1

    if (output_path := kwargs.get("output")) and not Path(output_path).is_dir():
        print_error(f"Output directory {output_path} is not a directory.")
        return 1

    if input_path.is_file():
        if input_path.suffix.lower() != ".yml":
            print_error(f"input {input_path} is not a valid yml file.")
            return 1
        _generate_docs_for_file(kwargs)

    # Add support for input which is a Playbooks directory and not a single yml file
    elif input_path.is_dir() and input_path.name == "Playbooks":
        for yml in input_path.glob("*.yml"):
            file_kwargs = copy.deepcopy(kwargs)
            file_kwargs["input"] = str(yml)
            _generate_docs_for_file(file_kwargs)

    else:
        print_error(
            f"Input {input_path} is neither a valid yml file, nor a folder named Playbooks."
        )
        return 1

    return 0


def _generate_docs_for_file(kwargs: Dict[str, Any]):
    """Helper function for supporting Playbooks directory as an input and not only a single yml file."""

    from demisto_sdk.commands.generate_docs.generate_integration_doc import (
        generate_integration_doc,
    )
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import (
        generate_playbook_doc,
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
    verbose: bool = kwargs.get("verbose", False)
    old_version: str = kwargs.get("old_version", "")
    skip_breaking_changes: bool = kwargs.get("skip_breaking_changes", False)
    custom_image_path: str = kwargs.get("custom_image_path", "")

    if command:
        if (
            output_path
            and (not os.path.isfile(os.path.join(output_path, "README.md")))
            or (not output_path)
            and (
                not os.path.isfile(
                    os.path.join(
                        os.path.dirname(os.path.realpath(input_path)), "README.md"
                    )
                )
            )
        ):
            print_error(
                "The `command` argument must be presented with existing `README.md` docs."
            )
            return 1

    file_type = find_type(kwargs.get("input", ""), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT, FileType.PLAYBOOK]:
        print_error("File is not an Integration, Script or a Playbook.")
        return 1

    if old_version and not os.path.isfile(old_version):
        print_error(f"Input old version file {old_version} was not found.")
        return 1

    if old_version and not old_version.lower().endswith(".yml"):
        print_error(f"Input old version {old_version} is not a valid yml file.")
        return 1

    if file_type == FileType.INTEGRATION:
        print(f"Generating {file_type.value.lower()} documentation")
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
            verbose=verbose,
            command=command,
            old_version=old_version,
            skip_breaking_changes=skip_breaking_changes,
        )
    elif file_type == FileType.SCRIPT:
        print(f"Generating {file_type.value.lower()} documentation")
        return generate_script_doc(
            input_path=input_path,
            output=output_path,
            examples=examples,
            permissions=permissions,
            limitations=limitations,
            insecure=insecure,
            verbose=verbose,
        )
    elif file_type == FileType.PLAYBOOK:
        print(f"Generating {file_type.value.lower()} documentation")
        return generate_playbook_doc(
            input_path=input_path,
            output=output_path,
            permissions=permissions,
            limitations=limitations,
            verbose=verbose,
            custom_image_path=custom_image_path,
        )
    else:
        print_error(f"File type {file_type.value} is not supported.")
        return 1


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
def create_id_set(**kwargs):
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
def merge_id_sets(**kwargs):
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
        print_error(
            f"Failed to merge ID sets: {first} with {second}, "
            f"there are entities with ID: {duplicates} that exist in both ID sets"
        )
        if fail_duplicates:
            sys.exit(1)


# ====================== update-release-notes =================== #
@main.command()
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
def update_release_notes(**kwargs):
    """Auto-increment pack version and generate release notes template."""
    from demisto_sdk.commands.update_release_notes.update_rn_manager import (
        UpdateReleaseNotesManager,
    )

    check_configuration_file("update-release-notes", kwargs)
    if kwargs.get("force") and not kwargs.get("input"):
        print_error(
            "Please add a specific pack in order to force a release notes update."
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
        print_error(f"An error occurred while updating the release notes: {str(e)}")
        sys.exit(1)


# ====================== find-dependencies ====================== #
@main.command()
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
    "-v",
    "--verbose",
    help="Whether to print the log to the console.",
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
def find_dependencies(**kwargs):
    """Find pack dependencies and update pack metadata."""
    from demisto_sdk.commands.find_dependencies.find_dependencies import (
        PackDependencies,
    )

    check_configuration_file("find-dependencies", kwargs)
    update_pack_metadata = not kwargs.get("no_update")
    input_paths = kwargs.get("input")  # since it can be multiple, received as a tuple
    verbose = kwargs.get("verbose", False)
    id_set_path = kwargs.get("id_set_path", "")
    use_pack_metadata = kwargs.get("use_pack_metadata", False)
    all_packs_dependencies = kwargs.get("all_packs_dependencies", False)
    get_dependent_on = kwargs.get("get_dependent_on", False)
    output_path = kwargs.get("output_path", ALL_PACKS_DEPENDENCIES_DEFAULT_PATH)
    dependency = kwargs.get("dependency", "")
    try:

        PackDependencies.find_dependencies_manager(
            id_set_path=str(id_set_path),
            verbose=verbose,
            update_pack_metadata=update_pack_metadata,
            use_pack_metadata=use_pack_metadata,
            input_paths=input_paths,
            all_packs_dependencies=all_packs_dependencies,
            get_dependent_on=get_dependent_on,
            output_path=output_path,
            dependency=dependency,
        )

    except ValueError as exp:
        print_error(str(exp))


# ====================== postman-codegen ====================== #
@main.command()
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
@click.option("--verbose", help="Print debug level logs", is_flag=True)
@click.option(
    "-p",
    "--package",
    help="Generated integration will be split to package format instead of a yml file.",
    is_flag=True,
)
@pass_config
def postman_codegen(
    config,
    input: IO,
    output: Path,
    name: str,
    output_prefix: str,
    command_prefix: str,
    config_out: bool,
    verbose: bool,
    package: bool,
):
    """Generates a Cortex XSOAR integration given a Postman collection 2.1 JSON file."""
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.postman_codegen.postman_codegen import (
        postman_to_autogen_configuration,
    )
    from demisto_sdk.commands.split.ymlsplitter import YmlSplitter

    if verbose:
        logger = logging_setup(verbose=3)
    else:
        logger = logging.getLogger("demisto-sdk")

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
            print_success(
                f"Package generated at {str(Path(output).absolute())} successfully"
            )
        else:
            print_success(
                f"Integration generated at {str(yml_path.absolute())} successfully"
            )


# ====================== generate-integration ====================== #
@main.command()
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
@click.option("--verbose", help="Print debug level logs", is_flag=True)
def generate_integration(input: IO, output: Path, verbose: bool):
    """Generates a Cortex XSOAR integration from a config json file,
    which is generated by commands like postman-codegen
    """
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.generate_integration.code_generator import (
        IntegrationGeneratorConfig,
    )

    if verbose:
        logging_setup(verbose=3)

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
@click.option("-v", "--verbose", is_flag=True, help="Be verbose with the log output")
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
def openapi_codegen(**kwargs):
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
    if not os.path.exists(output_dir):
        try:
            os.mkdir(output_dir)
        except Exception as err:
            print_error(f"Error creating directory {output_dir} - {err}")
            sys.exit(1)
    if not os.path.isdir(output_dir):
        print_error(f'The directory provided "{output_dir}" is not a directory')
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

    verbose = kwargs.get("verbose", False)
    fix_code = kwargs.get("fix_code", False)

    configuration = None
    if kwargs.get("config_file"):
        try:
            with open(kwargs["config_file"]) as config_file:
                configuration = json.load(config_file)
        except Exception as e:
            print_error(f"Failed to load configuration file: {e}")

    click.echo("Processing swagger file...")
    integration = OpenAPIIntegration(
        input_file,
        base_name,
        command_prefix,
        context_path,
        unique_keys=unique_keys,
        root_objects=root_objects,
        verbose=verbose,
        fix_code=fix_code,
        configuration=configuration,
    )

    integration.load_file()
    if not kwargs.get("config_file"):
        integration.save_config(integration.configuration, output_dir)
        print_success(f"Created configuration file in {output_dir}")
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
            if verbose:
                command_to_run = command_to_run + " -v"
            if fix_code:
                command_to_run = command_to_run + " -f"

            click.echo(
                f"Run the command again with the created configuration file(after a review): {command_to_run}"
            )
            sys.exit(0)

    if integration.save_package(output_dir):
        print_success(
            f"Successfully finished generating integration code and saved it in {output_dir}"
        )
    else:
        print_error(f"There was an error creating the package in {output_dir}")
        sys.exit(1)


# ====================== test-content command ====================== #
@main.command(
    short_help="""Created incidents for selected test-playbooks and gives a report about the results""",
    hidden=True,
)
@click.help_option("-h", "--help")
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
    "--server-type", help="Which server runs the tests? XSIAM or XSOAR", default="XSOAR"
)
@click.option(
    "-x", "--xsiam-machine", help="XSIAM machine to use, if it is XSIAM build."
)
@click.option("--xsiam-servers-path", help="Path to secret xsiam server metadata file.")
@click.option(
    "--xsiam-servers-api-keys-path", help="Path to file with XSIAM Servers api keys."
)
def test_content(**kwargs):
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
@main.command()
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
    "-pkw",
    "--use-packs-known-words",
    is_flag=True,
    help="Will find and load the known_words file from the pack. "
    "To use this option make sure you are running from the "
    "content directory.",
    default=False,
)
def doc_review(**kwargs):
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
def integration_diff(**kwargs):
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
    "-v",
    "--verbose",
    is_flag=True,
    type=bool,
    help="Indicate for extended prints.",
    required=False,
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    type=bool,
    help="Override existing yml file.",
    required=False,
)
def generate_yml_from_python(**kwargs):
    """
    Checks for differences between two versions of an integration, and verified that the new version covered the old version.
    """
    from demisto_sdk.commands.generate_yml_from_python.generate_yml import YMLGenerator

    yml_generator = YMLGenerator(
        filename=kwargs.get("input", ""),
        verbose=kwargs.get("verbose", False),
        force=kwargs.get("force", False),
    )
    yml_generator.generate()
    yml_generator.save_to_yml_file()


# ====================== convert ====================== #
@main.command()
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
def convert(config, **kwargs):
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
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Verbosity level -v / -vv / .. / -vvv",
    type=click.IntRange(0, 3, clamp=True),
    default=1,
    show_default=True,
)
@click.option("-i", "--input_path", help="Valid integration file path.", required=True)
@click.option(
    "-q", "--quiet", is_flag=True, help="Quiet output, only output results in the end"
)
@click.option(
    "-lp",
    "--log-path",
    help="Path to store all levels of logs",
    type=click.Path(resolve_path=True),
)
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
def generate_unit_tests(
    input_path: str = "",
    commands: list = [],
    output_dir: str = "",
    examples: str = "",
    insecure: bool = False,
    use_demisto: bool = False,
    append: bool = False,
    verbose: int = 1,
    quiet: bool = False,
    log_path: str = "",
):
    """
    This command is used to generate unit tests automatically from an  integration python code.
    Also supports generating unit tests for specific commands.
    """

    klara_logger = logging.getLogger("PYSCA")
    klara_logger.propagate = False
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.generate_unit_tests.generate_unit_tests import (
        run_generate_unit_tests,
    )

    logging_setup(
        verbose=verbose,  # type: ignore[arg-type]
        quiet=quiet,  # type: ignore[arg-type]
        log_path=log_path,
    )  # type: ignore[arg-type]
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
def error_code(config, **kwargs):
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
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Verbosity level -v / -vv / .. / -vvv",
    type=click.IntRange(0, 3, clamp=True),
    default=2,
    show_default=True,
)
@click.option(
    "-q", "--quiet", is_flag=True, help="Quiet output, only output results in the end"
)
@click.option(
    "-lp",
    "--log-path",
    help="Path to store all levels of logs",
    type=click.Path(resolve_path=True),
)
def create_content_graph(
    marketplace: str = MarketplaceVersions.XSOAR,
    no_dependencies: bool = False,
    output_path: Path = None,
    **kwargs,
):
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.content_graph.content_graph_commands import (
        create_content_graph as create_content_graph_command,
    )

    logging_setup(
        verbose=kwargs.get("verbose"),  # type: ignore[arg-type]
        quiet=kwargs.get("quiet"),  # type: ignore[arg-type]
        log_path=kwargs.get("log_path"),
    )  # type: ignore[arg-type]
    with Neo4jContentGraphInterface() as content_graph_interface:
        create_content_graph_command(
            content_graph_interface,
            marketplace=MarketplaceVersions(marketplace),
            dependencies=not no_dependencies,
            output_path=output_path,
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
    "--use-current",
    help="Whether to use the current content graph to update",
    default=False,
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
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Verbosity level -v / -vv / .. / -vvv",
    type=click.IntRange(0, 3, clamp=True),
    default=2,
    show_default=True,
)
@click.option(
    "-q", "--quiet", is_flag=True, help="Quiet output, only output results in the end"
)
@click.option(
    "-lp",
    "--log-path",
    help="Path to store all levels of logs",
    type=click.Path(resolve_path=True),
)
def update_content_graph(
    use_git: bool = False,
    marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    use_current: bool = False,
    imported_path: Path = None,
    packs: list = None,
    no_dependencies: bool = False,
    output_path: Path = None,
    **kwargs,
):
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.content_graph.content_graph_commands import (
        update_content_graph as update_content_graph_command,
    )
    from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
        Neo4jContentGraphInterface,
    )

    logging_setup(
        verbose=kwargs.get("verbose"),  # type: ignore[arg-type]
        quiet=kwargs.get("quiet"),  # type: ignore[arg-type]
        log_path=kwargs.get("log_path"),
    )  # type: ignore[arg-type]
    if packs and not isinstance(packs, list):
        # for some reason packs provided as tuple from click interface
        packs = list(packs)
    with Neo4jContentGraphInterface() as content_graph_interface:
        update_content_graph_command(
            content_graph_interface,
            marketplace=MarketplaceVersions(marketplace),
            use_git=use_git,
            imported_path=imported_path,
            use_current=use_current,
            packs_to_update=packs or [],
            dependencies=not no_dependencies,
            output_path=output_path,
        )


@main.result_callback()
def exit_from_program(result=0, **kwargs):
    sys.exit(result)


app = typer.Typer(name="modeling-rules", hidden=True, no_args_is_help=True)
app.command("test", no_args_is_help=True)(test_modeling_rule.test_modeling_rule)
app.command("init-test-data", no_args_is_help=True)(init_test_data.init_test_data)


typer_click_object = typer.main.get_command(app)
main.add_command(typer_click_object, "modeling-rules")


if __name__ == "__main__":
    main()
