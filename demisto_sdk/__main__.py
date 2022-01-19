# Site packages
import json
import logging
import os
import sys
import tempfile
from configparser import ConfigParser, MissingSectionHeaderError
from pathlib import Path
from typing import IO

# Third party packages
import click
import git
from pkg_resources import get_distribution

from demisto_sdk.commands.common.configuration import Configuration
# Common tools
from demisto_sdk.commands.common.constants import (
    ALL_PACKS_DEPENDENCIES_DEFAULT_PATH, FileType)
from demisto_sdk.commands.common.tools import (find_type,
                                               get_last_remote_release_version,
                                               get_release_note_entries,
                                               is_external_repository,
                                               print_error, print_success,
                                               print_warning)


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
        if ',' not in value:
            return super(PathsParamType, self).convert(value, param, ctx)

        split_paths = value.split(',')
        # check the validity of each of the paths
        _ = [super(PathsParamType, self).convert(path, param, ctx) for path in split_paths]
        return value


class VersionParamType(click.ParamType):
    """
    Defines a click options type for use with the @click.option decorator

    The type accepts a string represents a version number.
    """

    name = "version"

    def convert(self, value, param, ctx):
        version_sections = value.split('.')
        if len(version_sections) == 3 and \
                all(version_section.isdigit() for version_section in version_sections):
            return value
        else:
            self.fail(f"Version {value} is not according to the expected format. "
                      f"The format of version should be in x.y.z format, e.g: <2.1.3>", param, ctx)


class DemistoSDK:
    """
    The core class for the SDK.
    """

    def __init__(self):
        self.configuration = None


pass_config = click.make_pass_decorator(DemistoSDK, ensure=True)


def check_configuration_file(command, args):
    config_file_path = '.demisto-sdk-conf'
    true_synonyms = ['true', 'True', 't', '1']
    if os.path.isfile(config_file_path):
        try:
            config = ConfigParser(allow_no_value=True)
            config.read(config_file_path)

            if command in config.sections():
                for key in config[command]:
                    if key in args:
                        # if the key exists in the args we will run it over if it is either:
                        # a - a flag currently not set and is defined in the conf file
                        # b - not a flag but an arg that is currently None and there is a value for it in the conf file
                        if args[key] is False and config[command][key] in true_synonyms:
                            args[key] = True

                        elif args[key] is None and config[command][key] is not None:
                            args[key] = config[command][key]

                    # if the key does not exist in the current args, add it
                    else:
                        if config[command][key] in true_synonyms:
                            args[key] = True

                        else:
                            args[key] = config[command][key]

        except MissingSectionHeaderError:
            pass


@click.group(invoke_without_command=True, no_args_is_help=True, context_settings=dict(max_content_width=100), )
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-v', '--version', help='Get the demisto-sdk version.',
    is_flag=True, default=False, show_default=True
)
@click.option(
    '-rn', '--release-notes', help='Get the release notes of the current demisto-sdk version.',
    is_flag=True, default=False, show_default=True
)
@pass_config
def main(config, version, release_notes):
    import dotenv
    dotenv.load_dotenv()  # Load a .env file from the cwd.
    config.configuration = Configuration()
    if not os.getenv('DEMISTO_SDK_SKIP_VERSION_CHECK') or version:  # If the key exists/called to version
        cur_version = get_distribution('demisto-sdk').version
        last_release = get_last_remote_release_version()
        print_warning(f'You are using demisto-sdk {cur_version}.')
        if last_release and cur_version != last_release:
            print_warning(f'however version {last_release} is available.\n'
                          f'You should consider upgrading via "pip3 install --upgrade demisto-sdk" command.')
        if release_notes:
            rn_entries = get_release_note_entries(cur_version)

            if not rn_entries:
                print_warning('\nCould not get the release notes for this version.')
            else:
                click.echo('\nThe following are the release note entries for the current version:\n')
                for rn in rn_entries:
                    click.echo(rn)
                click.echo('')


# ====================== split ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input', help='The yml/json file to extract from', required=True
)
@click.option(
    '-o', '--output',
    help="The output dir to write the extracted code/description/image/json to."
)
@click.option(
    '--no-demisto-mock',
    help="Don't add an import for demisto mock. (only for yml files)",
    is_flag=True,
    show_default=True
)
@click.option(
    '--no-common-server',
    help="Don't add an import for CommonServerPython. (only for yml files)",
    is_flag=True,
    show_default=True
)
@click.option(
    '--no-auto-create-dir',
    help="Don't auto create the directory if the target directory ends with *Integrations/*Scripts/*Dashboards"
         "/*GenericModules.",
    is_flag=True,
    show_default=True
)
@click.option(
    '--no-pipenv',
    help="Don't auto create pipenv for requirements installation. (only for yml files)",
    is_flag=True,
    show_default=True
)
@click.option(
    '--new-module-file',
    help="Create a new module file instead of editing the existing file. (only for json files)",
    is_flag=True,
    show_default=True
)
@pass_config
def split(config, **kwargs):
    """Split the code, image and description files from a Demisto integration or script yaml file
    to multiple files(To a package format - https://demisto.pan.dev/docs/package-dir).
    """
    from demisto_sdk.commands.split.jsonsplitter import JsonSplitter
    from demisto_sdk.commands.split.ymlsplitter import YmlSplitter

    check_configuration_file('split', kwargs)
    file_type: FileType = find_type(kwargs.get('input', ''), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT, FileType.GENERIC_MODULE]:
        print_error('File is not an Integration, Script or Generic Module.')
        return 1

    if file_type in [FileType.INTEGRATION, FileType.SCRIPT]:
        yml_splitter = YmlSplitter(configuration=config.configuration, file_type=file_type.value, **kwargs)
        return yml_splitter.extract_to_package_format()

    else:
        json_splitter = JsonSplitter(input=kwargs.get('input'), output=kwargs.get('output'),  # type: ignore[arg-type]
                                     no_auto_create_dir=kwargs.get('no_auto_create_dir'),  # type: ignore[arg-type]
                                     no_logging=kwargs.get('no_logging'),  # type: ignore[arg-type]
                                     new_module_file=kwargs.get('new_module_file'))  # type: ignore[arg-type]
        return json_splitter.split_json()


# ====================== extract-code ====================== #
@main.command(hidden=True)
@click.help_option(
    '-h', '--help'
)
@click.option(
    '--input', '-i',
    help='The yml file to extract from',
    required=True
)
@click.option(
    '--output', '-o',
    required=True,
    help="The output file to write the code to"
)
@click.option(
    '--no-demisto-mock',
    help="Don't add an import for demisto mock, false by default",
    is_flag=True,
    show_default=True
)
@click.option(
    '--no-common-server',
    help="Don't add an import for CommonServerPython."
         "If not specified will import unless this is CommonServerPython",
    is_flag=True,
    show_default=True
)
@pass_config
def extract_code(config, **kwargs):
    """Extract code from a Demisto integration or script yaml file."""
    from demisto_sdk.commands.split.ymlsplitter import YmlSplitter
    check_configuration_file('extract-code', kwargs)
    file_type: FileType = find_type(kwargs.get('input', ''), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT]:
        print_error('File is not an Integration or Script.')
        return 1
    extractor = YmlSplitter(configuration=config.configuration, file_type=file_type.value, **kwargs)
    return extractor.extract_code(kwargs['outfile'])


# ====================== unify ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input", help="The directory path to the files to unify", required=True, type=click.Path(dir_okay=True)
)
@click.option(
    "-o", "--output", help="The output dir to write the unified yml to", required=False
)
@click.option(
    "--force", help="Forcefully overwrites the preexisting yml if one exists",
    is_flag=True,
    show_default=False
)
def unify(**kwargs):
    """
    This command has two main functions:

    1. YML Unifier - Unifies integration/script code, image, description and yml files to a single XSOAR yml file.
     * Note that this should be used on a single integration/script and not a pack, not multiple scripts/integrations.
     * To use this function - set as input a path to the *directory* of the integration/script to unify.

    2. GenericModule Unifier - Unifies a GenericModule with its Dashboards to a single JSON object.
     * To use this function - set as input a path to a GenericModule *file*.
    """
    check_configuration_file('unify', kwargs)
    # Input is of type Path.
    kwargs['input'] = str(kwargs['input'])
    file_type = find_type(kwargs['input'])
    if file_type == FileType.GENERIC_MODULE:
        from demisto_sdk.commands.unify.generic_module_unifier import \
            GenericModuleUnifier

        # pass arguments to GenericModule unifier and call the command
        generic_module_unifier = GenericModuleUnifier(**kwargs)
        generic_module_unifier.merge_generic_module_with_its_dashboards()

    else:
        from demisto_sdk.commands.unify.yml_unifier import YmlUnifier

        # pass arguments to YML unifier and call the command
        yml_unifier = YmlUnifier(**kwargs)
        yml_unifier.merge_script_package_to_yml()

    return 0


# ====================== zip-packs ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option('-i', '--input',
              help="The packs to be zipped as csv list of pack paths.",
              type=PathsParamType(exists=True, resolve_path=True),
              required=True)
@click.option('-o', '--output', help='The destination directory to create the packs.',
              type=click.Path(file_okay=False, resolve_path=True), required=True)
@click.option('-v', '--content-version', help='The content version in CommonServerPython.', default='0.0.0')
@click.option('-u', '--upload', is_flag=True, help='Upload the unified packs to the marketplace.', default=False)
@click.option('--zip-all', is_flag=True, help='Zip all the packs in one zip file.', default=False)
def zip_packs(**kwargs) -> int:
    """Generating zipped packs that are ready to be uploaded to Cortex XSOAR machine."""
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.upload.uploader import Uploader
    from demisto_sdk.commands.zip_packs.packs_zipper import (EX_FAIL,
                                                             EX_SUCCESS,
                                                             PacksZipper)
    logging_setup(3)
    check_configuration_file('zip-packs', kwargs)

    # if upload is true - all zip packs will be compressed to one zip file
    should_upload = kwargs.pop('upload', False)
    zip_all = kwargs.pop('zip_all', False) or should_upload

    packs_zipper = PacksZipper(zip_all=zip_all, pack_paths=kwargs.pop('input'), quiet_mode=zip_all, **kwargs)
    zip_path, unified_pack_names = packs_zipper.zip_packs()

    if should_upload and zip_path:
        return Uploader(input=zip_path, pack_names=unified_pack_names).upload()

    return EX_SUCCESS if zip_path is not None else EX_FAIL


# ====================== validate ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    '--no-conf-json', is_flag=True,
    default=False, show_default=True, help='Skip conf.json validation.')
@click.option(
    '-s', '--id-set', is_flag=True,
    default=False, show_default=True, help='Perform validations using the id_set file.')
@click.option(
    "-idp", "--id-set-path", help="The path of the id-set.json used for validations.",
    type=click.Path(resolve_path=True))
@click.option(
    '--prev-ver', help='Previous branch or SHA1 commit to run checks against.')
@click.option(
    '--no-backward-comp', is_flag=True, show_default=True,
    help='Whether to check backward compatibility or not.')
@click.option(
    '-g', '--use-git', is_flag=True, show_default=True,
    default=False,
    help='Validate changes using git - this will check current branch\'s changes against origin/master or origin/main. '
         'If the --post-commit flag is supplied: validation will run only on the current branch\'s changed files '
         'that have been committed. '
         'If the --post-commit flag is not supplied: validation will run on all changed files in the current branch, '
         'both committed and not committed. ')
@click.option(
    '-pc', '--post-commit',
    is_flag=True,
    help='Whether the validation should run only on the current branch\'s committed changed files. '
         'This applies only when the -g flag is supplied.'
)
@click.option(
    '-st', '--staged',
    is_flag=True,
    help='Whether the validation should ignore unstaged files.'
         'This applies only when the -g flag is supplied.'
)
@click.option(
    '-iu', '--include-untracked',
    is_flag=True,
    help='Whether to include untracked files in the validation. '
         'This applies only when the -g flag is supplied.'
)
@click.option(
    '-a', '--validate-all', is_flag=True, show_default=True, default=False,
    help='Whether to run all validation on all files or not.'
)
@click.option(
    '-i', '--input', type=click.Path(exists=True, resolve_path=True),
    help='The path of the content pack/file to validate specifically.'
)
@click.option(
    '--skip-pack-release-notes', is_flag=True,
    help='Skip validation of pack release notes.')
@click.option(
    '--print-ignored-errors', is_flag=True,
    help='Print ignored errors as warnings.')
@click.option(
    '--print-ignored-files', is_flag=True,
    help='Print which files were ignored by the command.')
@click.option(
    '--no-docker-checks', is_flag=True,
    help='Whether to run docker image validation.')
@click.option(
    '--silence-init-prints', is_flag=True,
    help='Whether to skip the initialization prints.')
@click.option(
    '--skip-pack-dependencies', is_flag=True,
    help='Skip validation of pack dependencies.')
@click.option(
    '--create-id-set', is_flag=True,
    help='Whether to create the id_set.json file.')
@click.option(
    '-j', '--json-file', help='The JSON file path to which to output the command results.')
@click.option(
    '--skip-schema-check', is_flag=True,
    help='Whether to skip the file schema check.')
@click.option(
    '--debug-git', is_flag=True,
    help='Whether to print debug logs for git statuses.')
@click.option(
    '--print-pykwalify', is_flag=True,
    help='Whether to print the pykwalify log errors.')
@click.option(
    "--quite-bc-validation",
    help="Set backwards compatibility validation's errors as warnings.",
    is_flag=True)
@click.option(
    "--allow-skipped",
    help="Don't fail on skipped integrations or when all test playbooks are skipped.",
    is_flag=True)
@pass_config
def validate(config, **kwargs):
    """Validate your content files. If no additional flags are given, will validated only committed files."""
    from demisto_sdk.commands.validate.validate_manager import ValidateManager
    check_configuration_file('validate', kwargs)
    sys.path.append(config.configuration.env_dir)

    file_path = kwargs['input']

    if kwargs['post_commit'] and kwargs['staged']:
        print_error('Could not supply the staged flag with the post-commit flag')
        sys.exit(1)
    try:
        is_external_repo = is_external_repository()
        # default validate to -g --post-commit
        if not kwargs.get('validate_all') and not kwargs['use_git'] and not file_path:
            kwargs['use_git'] = True
            kwargs['post_commit'] = True
        validator = ValidateManager(
            is_backward_check=not kwargs['no_backward_comp'],
            only_committed_files=kwargs['post_commit'], prev_ver=kwargs['prev_ver'],
            skip_conf_json=kwargs['no_conf_json'], use_git=kwargs['use_git'],
            file_path=file_path,
            validate_all=kwargs.get('validate_all'),
            validate_id_set=kwargs['id_set'],
            skip_pack_rn_validation=kwargs['skip_pack_release_notes'],
            print_ignored_errors=kwargs['print_ignored_errors'],
            is_external_repo=is_external_repo,
            print_ignored_files=kwargs['print_ignored_files'],
            no_docker_checks=kwargs['no_docker_checks'],
            silence_init_prints=kwargs['silence_init_prints'],
            skip_dependencies=kwargs['skip_pack_dependencies'],
            id_set_path=kwargs.get('id_set_path'),
            staged=kwargs['staged'],
            create_id_set=kwargs.get('create_id_set'),
            json_file_path=kwargs.get('json_file'),
            skip_schema_check=kwargs.get('skip_schema_check'),
            debug_git=kwargs.get('debug_git'),
            include_untracked=kwargs.get('include_untracked'),
            quite_bc=kwargs.get('quite_bc_validation'),
            check_is_unskipped=not kwargs.get('allow_skipped', False),
        )
        return validator.run_validation()
    except (git.InvalidGitRepositoryError, git.NoSuchPathError, FileNotFoundError) as e:
        print_error(e)
        print_error("\nYou may not be running `demisto-sdk validate` command in the content directory.\n"
                    "Please run the command from content directory")
        sys.exit(1)


# ====================== create-content-artifacts ====================== #
@main.command(hidden=True)
@click.help_option(
    '-h', '--help'
)
@click.option('-a', '--artifacts_path', help='Destination directory to create the artifacts.',
              type=click.Path(file_okay=False, resolve_path=True), required=True)
@click.option('--zip/--no-zip', help='Zip content artifacts folders', default=True)
@click.option('--packs', help='Create only content_packs artifacts. '
                              'Used for server version 5.5.0 and earlier.', is_flag=True)
@click.option('-v', '--content_version', help='The content version in CommonServerPython.', default='0.0.0')
@click.option('-s', '--suffix', help='Suffix to add all yaml/json/yml files in the created artifacts.')
@click.option('--cpus',
              help='Number of cpus/vcpus available - only required when os not reflect number of cpus (CircleCI'
                   'always show 32, but medium has 3.', hidden=True, default=os.cpu_count())
@click.option('-idp', '--id-set-path', help='The full path of id_set.json', hidden=True,
              type=click.Path(exists=True, resolve_path=True))
@click.option('-p', '--pack-names',
              help=("Packs to create artifacts for. Optional values are: `all` or "
                    "csv list of packs. "
                    "Default is set to `all`"),
              default="all", hidden=True)
@click.option('-sk', '--signature-key', help='Base64 encoded signature key used for signing packs.', hidden=True)
@click.option('-sd', '--sign-directory', help='Path to the signDirectory executable file.',
              type=click.Path(exists=True, resolve_path=True), hidden=True)
@click.option('-rt', '--remove-test-playbooks', is_flag=True,
              help='Should remove test playbooks from content packs or not.', default=True, hidden=True)
@click.option('-mp', '--marketplace', help='The marketplace the artifacts are created for, that '
                                           'determines which artifacts are created for each pack. '
                                           'Default is the XSOAR marketplace, that has all of the packs '
                                           'artifacts.', default='xsoar', type=click.Choice(['xsoar', 'marketplacev2', 'v2']))
@click.option('-fbi', '--filter-by-id-set', is_flag=True,
              help='Whether to use the id set as content items guide, meaning only include in the packs the '
                   'content items that appear in the id set.', default=False, hidden=True)
def create_content_artifacts(**kwargs) -> int:
    """Generating the following artifacts:
       1. content_new - Contains all content objects of type json,yaml (from_version < 6.0.0)
       2. content_packs - Contains all packs from Packs - Ignoring internal files (to_version >= 6.0.0).
       3. content_test - Contains all test scripts/playbooks (from_version < 6.0.0)
       4. content_all - Contains all from content_new and content_test.
       5. uploadable_packs - Contains zipped packs that are ready to be uploaded to Cortex XSOAR machine.
    """
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import \
        ArtifactsManager
    logging_setup(3)
    check_configuration_file('create-content-artifacts', kwargs)
    artifacts_conf = ArtifactsManager(**kwargs)
    return artifacts_conf.create_content_artifacts()


# ====================== secrets ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input', help='Specify file of to check secret on.'
)
@click.option(
    '--post-commit',
    is_flag=True,
    show_default=True,
    help='Whether the secretes is done after you committed your files, '
         'this will help the command to determine which files it should check in its '
         'run. Before you commit the files it should not be used. Mostly for build '
         'validations.'
)
@click.option(
    '-ie', '--ignore-entropy',
    is_flag=True,
    help='Ignore entropy algorithm that finds secret strings (passwords/api keys).'
)
@click.option(
    '-wl', '--whitelist',
    default='./Tests/secrets_white_list.json',
    show_default=True,
    help='Full path to whitelist file, file name should be "secrets_white_list.json"'
)
@click.option(
    '--prev-ver',
    help='The branch against which to run secrets validation.'
)
@pass_config
def secrets(config, **kwargs):
    """Run Secrets validator to catch sensitive data before exposing your code to public repository.
     Attach path to whitelist to allow manual whitelists.
     """
    from demisto_sdk.commands.secrets.secrets import SecretsValidator
    check_configuration_file('secrets', kwargs)
    sys.path.append(config.configuration.env_dir)
    secrets_validator = SecretsValidator(
        configuration=config.configuration,
        is_circle=kwargs['post_commit'],
        ignore_entropy=kwargs['ignore_entropy'],
        white_list_path=kwargs['whitelist'],
        input_path=kwargs.get('input')
    )
    return secrets_validator.run()


# ====================== lint ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input", help="Specify directory(s) of integration/script",
    type=PathsParamType(exists=True, resolve_path=True)
)
@click.option("-g", "--git", is_flag=True, help="Will run only on changed packages")
@click.option("-a", "--all-packs", is_flag=True, help="Run lint on all directories in content repo")
@click.option('-v', "--verbose", count=True, help="Verbosity level -v / -vv / .. / -vvv",
              type=click.IntRange(0, 3, clamp=True), default=2, show_default=True)
@click.option('-q', "--quiet", is_flag=True, help="Quiet output, only output results in the end")
@click.option("-p", "--parallel", default=1, help="Run tests in parallel", type=click.IntRange(0, 15, clamp=True),
              show_default=True)
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
@click.option("--prev-ver", help="Previous branch or SHA1 commit to run checks against", default='master')
@click.option("--test-xml", help="Path to store pytest xml results", type=click.Path(exists=True, resolve_path=True))
@click.option("--failure-report", help="Path to store failed packs report",
              type=click.Path(exists=True, resolve_path=True))
@click.option("-lp", "--log-path", help="Path to store all levels of logs",
              type=click.Path(resolve_path=True))
@click.option("-j", "--json-file", help="The JSON file path to which to output the command results.",
              type=click.Path(resolve_path=True))
@click.option("--no-coverage", is_flag=True, help="Do NOT run coverage report.")
@click.option(
    "--coverage-report", help="Specify directory for the coverage report files",
    type=PathsParamType()
)
@click.option("-dt", "--docker-timeout", default=60,
              help="The timeout (in seconds) for requests done by the docker client.", type=int)
@click.option("-idp", "--id-set-path", help="Path to id_set.json, relevant for when using the "
                                            "--check-dependent-api-module flag.",
              type=click.Path(resolve_path=True),
              default='Tests/id_set.json')
@click.option("-cdam", "--check-dependent-api-module", is_flag=True, help="Run unit tests and lint on all packages that "
              "are dependent on the found "
              "modified api modules.", default=True)
def lint(**kwargs):
    """Lint command will perform:
        1. Package in host checks - flake8, bandit, mypy, vulture.
        2. Package in docker image checks -  pylint, pytest, powershell - test, powershell - analyze.
        Meant to be used with integrations/scripts that use the folder (package) structure.
        Will lookup up what docker image to use and will setup the dev dependencies and file in the target folder.
        If no additional flags specifying the packs are given,will lint only changed files.
    """
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.lint.lint_manager import LintManager
    logging_setup(verbose=kwargs.get('verbose'),  # type: ignore[arg-type]
                  quiet=kwargs.get('quiet'),  # type: ignore[arg-type]
                  log_path=kwargs.get('log_path'))  # type: ignore[arg-type]

    check_configuration_file('lint', kwargs)
    lint_manager = LintManager(
        input=kwargs.get('input'),  # type: ignore[arg-type]
        git=kwargs.get('git'),  # type: ignore[arg-type]
        all_packs=kwargs.get('all_packs'),  # type: ignore[arg-type]
        verbose=kwargs.get('verbose'),  # type: ignore[arg-type]
        quiet=kwargs.get('quiet'),  # type: ignore[arg-type]
        prev_ver=kwargs.get('prev_ver'),  # type: ignore[arg-type]
        json_file_path=kwargs.get('json_file'),  # type: ignore[arg-type]
        id_set_path=kwargs.get('id_set_path'),  # type: ignore[arg-type]
        check_dependent_api_module=kwargs.get('check_dependent_api_module'),  # type: ignore[arg-type]
    )
    return lint_manager.run_dev_packages(
        parallel=kwargs.get('parallel'),  # type: ignore[arg-type]
        no_flake8=kwargs.get('no_flake8'),  # type: ignore[arg-type]
        no_bandit=kwargs.get('no_bandit'),  # type: ignore[arg-type]
        no_mypy=kwargs.get('no_mypy'),  # type: ignore[arg-type]
        no_vulture=kwargs.get('no_vulture'),  # type: ignore[arg-type]
        no_xsoar_linter=kwargs.get('no_xsoar_linter'),  # type: ignore[arg-type]
        no_pylint=kwargs.get('no_pylint'),  # type: ignore[arg-type]
        no_test=kwargs.get('no_test'),  # type: ignore[arg-type]
        no_pwsh_analyze=kwargs.get('no_pwsh_analyze'),  # type: ignore[arg-type]
        no_pwsh_test=kwargs.get('no_pwsh_test'),  # type: ignore[arg-type]
        keep_container=kwargs.get('keep_container'),  # type: ignore[arg-type]
        test_xml=kwargs.get('test_xml'),  # type: ignore[arg-type]
        failure_report=kwargs.get('failure_report'),  # type: ignore[arg-type]
        no_coverage=kwargs.get('no_coverage'),  # type: ignore[arg-type]
        coverage_report=kwargs.get('coverage_report'),  # type: ignore[arg-type]
        docker_timeout=kwargs.get('docker_timeout'),  # type: ignore[arg-type]
    )


# ====================== coverage-analyze ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input", help="The .coverage file to analyze.",
    default=os.path.join('coverage_report', '.coverage'),
    type=PathsParamType(exists=True, resolve_path=True)
)
@click.option(
    "--default-min-coverage", help="Default minimum coverage (for new files).",
    default=70.0, type=click.FloatRange(0.0, 100.0)
)
@click.option(
    "--allowed-coverage-degradation-percentage", help="Allowed coverage degradation percentage (for modified files).",
    default=1.0, type=click.FloatRange(0.0, 100.0)
)
@click.option(
    "--no-cache", help="Force download of the previous coverage report file.",
    is_flag=True, type=bool)
@click.option(
    "--report-dir", help="Directory of the coverage report files.",
    default='coverage_report', type=PathsParamType(resolve_path=True))
@click.option(
    "--report-type", help="The type of coverage report (posible values: 'text', 'html', 'xml', 'json' or 'all').", type=str)
@click.option("--no-min-coverage-enforcement", help="Do not enforce minimum coverage.", is_flag=True)
@click.option(
    "--previous-coverage-report-url", help="URL of the previous coverage report.",
    default='https://storage.googleapis.com/marketplace-dist-dev/code-coverage-reports/coverage-min.json', type=str
)
def coverage_analyze(**kwargs):
    from demisto_sdk.commands.coverage_analyze.coverage_report import \
        CoverageReport
    try:
        no_degradation_check = kwargs['allowed_coverage_degradation_percentage'] == 100.0
        no_min_coverage_enforcement = kwargs['no_min_coverage_enforcement']

        cov_report = CoverageReport(
            default_min_coverage=kwargs['default_min_coverage'],
            allowed_coverage_degradation_percentage=kwargs['allowed_coverage_degradation_percentage'],
            coverage_file=kwargs['input'],
            no_cache=kwargs.get('no_cache', False),
            report_dir=kwargs['report_dir'],
            report_type=kwargs['report_type'],
            no_degradation_check=no_degradation_check,
            previous_coverage_report_url=kwargs['previous_coverage_report_url']
        )
        cov_report.coverage_report()
        # if no_degradation_check=True we will suppress the minimum coverage check
        if no_degradation_check or cov_report.coverage_diff_report() or no_min_coverage_enforcement:
            return 0
    except Exception as error:
        logging.getLogger('demisto-sdk').error(error)

    return 1


# ====================== format ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input", help="The path of the script yml file\n"
                          "If no input is specified, the format will be executed on all new/changed files.",
    type=click.Path(exists=True, resolve_path=True))
@click.option(
    "-o", "--output", help="The path where the formatted file will be saved to",
    type=click.Path(resolve_path=True))
@click.option(
    "-fv", "--from-version", help="Specify fromversion of the pack")
@click.option(
    "-nv", "--no-validate", help="Set when validate on file is not wanted", is_flag=True)
@click.option(
    "-ud", "--update-docker", help="Set if you want to update the docker image of the integration/script", is_flag=True)
@click.option(
    "-v", "--verbose", help="Verbose output", is_flag=True)
@click.option(
    "-y", "--assume-yes",
    help="Automatic yes to prompts; assume 'yes' as answer to all prompts and run non-interactively",
    is_flag=True)
@click.option(
    "-d", "--deprecate", help="Set if you want to deprecate the integration/script/playbook", is_flag=True)
@click.option(
    "-g", "--use-git",
    help="Use git to automatically recognize which files changed and run format on them.",
    is_flag=True)
@click.option(
    '--prev-ver', help='Previous branch or SHA1 commit to run checks against.')
@click.option(
    '-iu', '--include-untracked',
    is_flag=True,
    help='Whether to include untracked files in the formatting.'
)
@click.option(
    '-at', '--add-tests',
    is_flag=True,
    help='Whether to answer manually to add tests configuration prompt when running interactively.'
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
        add_tests: bool
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
    )


# ====================== upload ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input",
    type=PathsParamType(exists=True, resolve_path=True),
    help="The path of file or a directory to upload. The following are supported:\n"
         "- Pack\n"
         "- A content entity directory that is inside a pack. For example: an Integrations "
         "directory or a Layouts directory.\n"
         "- Valid file that can be imported to Cortex XSOAR manually. For example a playbook: "
         "helloWorld.yml", required=False
)
@click.option(
    "--input-config-file",
    type=PathsParamType(exists=True, resolve_path=True),
    help="The path to the config file to download all the custom packs from", required=False
)
@click.option(
    "-z", "--zip",
    help="Compress the pack to zip before upload, this flag is relevant only for packs.", is_flag=True
)
@click.option(
    "--keep-zip", help="Directory where to store the zip after creation, this argument is relevant only for packs "
                       "and in case the --zip flag is used.", required=False, type=click.Path(exists=True))
@click.option(
    "--insecure",
    help="Skip certificate validation", is_flag=True
)
@click.option(
    "-v", "--verbose",
    help="Verbose output", is_flag=True
)
def upload(**kwargs):
    """Upload integration or pack to Demisto instance.
    DEMISTO_BASE_URL environment variable should contain the Demisto server base URL.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    * Note: Uploading classifiers to Cortex XSOAR is available from version 6.0.0 and up. *
    """
    from demisto_sdk.commands.upload.uploader import ConfigFileParser, Uploader
    from demisto_sdk.commands.zip_packs.packs_zipper import (EX_FAIL,
                                                             PacksZipper)
    if kwargs['zip'] or kwargs['input_config_file']:
        if kwargs.pop('zip', False):
            pack_path = kwargs['input']
            kwargs.pop('input_config_file')

        else:
            config_file_path = kwargs['input_config_file']
            config_file_to_parse = ConfigFileParser(config_file_path=config_file_path)
            pack_path = config_file_to_parse.parse_file()
            kwargs.pop('input_config_file')

        output_zip_path = kwargs.pop('keep_zip') or tempfile.gettempdir()
        packs_unifier = PacksZipper(pack_paths=pack_path, output=output_zip_path,
                                    content_version='0.0.0', zip_all=True, quiet_mode=True)
        packs_zip_path, pack_names = packs_unifier.zip_packs()
        if packs_zip_path is None:
            return EX_FAIL

        kwargs['input'] = packs_zip_path
        kwargs['pack_names'] = pack_names
    else:
        kwargs.pop('zip')
        kwargs.pop('keep_zip')
        kwargs.pop('input_config_file')

    check_configuration_file('upload', kwargs)
    return Uploader(**kwargs).upload()


# ====================== download ====================== #


@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-o", "--output", help="The path of a package directory to download custom content to", required=False,
    multiple=False)
@click.option(
    "-i", "--input", help="Custom content file name to be downloaded. Can be provided multiple times",
    required=False, multiple=True)
@click.option(
    "-r", "--regex", help="Regex Pattern, download all the custom content files that match this regex pattern.",
    required=False)
@click.option(
    "--insecure", help="Skip certificate validation", is_flag=True)
@click.option(
    "-v", "--verbose", help="Verbose output", is_flag=True)
@click.option(
    "-f", "--force", help="Whether to override existing files or not", is_flag=True)
@click.option(
    "-lf", "--list-files", help="Prints a list of all custom content files available to be downloaded", is_flag=True)
@click.option(
    "-a", "--all-custom-content", help="Download all available custom content files", is_flag=True)
@click.option(
    "-fmt", "--run-format", help="Whether to run demisto-sdk format on downloaded files or not", is_flag=True)
def download(**kwargs):
    """Download custom content from Demisto instance.
    DEMISTO_BASE_URL environment variable should contain the Demisto server base URL.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    """
    from demisto_sdk.commands.download.downloader import Downloader
    check_configuration_file('download', kwargs)
    downloader: Downloader = Downloader(**kwargs)
    return downloader.download()


# ====================== update-xsoar-config-file ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-pi", "--pack-id", help="The Pack ID to add to XSOAR Configuration File", required=False,
    multiple=False)
@click.option(
    "-pd", "--pack-data", help="The Pack Data to add to XSOAR Configuration File - "
           "Pack URL for Custom Pack and Pack Version for OOTB Pack", required=False, multiple=False)
@click.option(
    "-mp", "--add-marketplace-pack", help="Add a Pack to the MarketPlace Packs section in the Configuration File",
    required=False, is_flag=True)
@click.option(
    "-cp", "--add-custom-pack", help="Add the Pack to the Custom Packs section in the Configuration File",
    is_flag=True)
@click.option(
    "-all", "--add-all-marketplace-packs",
    help="Add all the installed MarketPlace Packs to the marketplace_packs in XSOAR Configuration File", is_flag=True)
@click.option(
    "--insecure", help="Skip certificate validation", is_flag=True)
@click.option(
    "--file-path", help="XSOAR Configuration File path, the default value is in the repo level", is_flag=False)
def xsoar_config_file_update(**kwargs):
    """Download custom content from Demisto instance.
    DEMISTO_BASE_URL environment variable should contain the Demisto server base URL.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    """
    from demisto_sdk.commands.update_xsoar_config_file.update_xsoar_config_file import \
        XSOARConfigFileUpdater
    file_updater: XSOARConfigFileUpdater = XSOARConfigFileUpdater(**kwargs)
    return file_updater.update()


# ====================== run ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-q", "--query", help="The query to run", required=True)
@click.option(
    "--insecure", help="Skip certificate validation", is_flag=True)
@click.option(
    "-v", "--verbose", help="Verbose output", is_flag=True)
@click.option(
    "-D", "--debug", help="Whether to enable the debug-mode feature or not, if you want to save the output file "
                          "please use the --debug-path option", is_flag=True)
@click.option(
    "--debug-path", help="The path to save the debug file at, if not specified the debug file will be printed to the "
                         "terminal")
@click.option(
    "--json-to-outputs", help="Whether to run json_to_outputs command on the context output of the query. If the "
                              "context output does not exists or the `-r` flag is used, will use the raw"
                              " response of the query", is_flag=True)
@click.option(
    "-p", "--prefix", help="Used with `json-to-outputs` flag. Output prefix e.g. Jira.Ticket, VirusTotal.IP, "
                           "the base path for the outputs that the script generates")
@click.option(
    "-r", "--raw-response", help="Used with `json-to-outputs` flag. Use the raw response of the query for"
                                 " `json-to-outputs`", is_flag=True)
def run(**kwargs):
    """Run integration command on remote Demisto instance in the playground.
    DEMISTO_BASE_URL environment variable should contain the Demisto base URL.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    """
    from demisto_sdk.commands.run_cmd.runner import Runner
    check_configuration_file('run', kwargs)
    runner = Runner(**kwargs)
    return runner.run()


# ====================== run-playbook ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    '--url', '-u',
    help='URL to a Demisto instance. You can also specify the URL as an environment variable named: DEMISTO_BASE_URL'
)
@click.option(
    '--playbook_id', '-p',
    help="The playbook ID to run.",
    required=True
)
@click.option(
    '--wait', '-w', is_flag=True,
    help="Wait until the playbook run is finished and get a response."
)
@click.option(
    '--timeout', '-t',
    default=90,
    show_default=True,
    help="Timeout for the command. The playbook will continue to run in Demisto"
)
@click.option(
    "--insecure", help="Skip certificate validation.", is_flag=True)
def run_playbook(**kwargs):
    """Run a playbook in Demisto.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    Example: DEMISTO_API_KEY=<API KEY> demisto-sdk run-playbook -p 'p_name' -u
    'https://demisto.local'.
    """
    from demisto_sdk.commands.run_playbook.playbook_runner import \
        PlaybookRunner
    check_configuration_file('run-playbook', kwargs)
    playbook_runner = PlaybookRunner(**kwargs)
    return playbook_runner.run_playbook()


# ====================== run-test-playbook ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-tpb', '--test-playbook-path',
    help="Path to test playbook to run, "
         "can be a path to specific test playbook or path to pack name for example: Packs/GitHub.",
    required=False
)
@click.option(
    '--all', is_flag=True,
    help="Run all the test playbooks from this repository."
)
@click.option(
    '--wait', '-w', is_flag=True, default=True,
    help="Wait until the test-playbook run is finished and get a response."
)
@click.option(
    '--timeout', '-t',
    default=90,
    show_default=True,
    help="Timeout for the command. The test-playbook will continue to run in your instance"
)
@click.option(
    "--insecure", help="Skip certificate validation.", is_flag=True)
def run_test_playbook(**kwargs):
    """Run a test playbooks in your instance."""
    from demisto_sdk.commands.run_test_playbook.test_playbook_runner import \
        TestPlaybookRunner
    check_configuration_file('run-test-playbook', kwargs)
    test_playbook_runner = TestPlaybookRunner(**kwargs)
    return test_playbook_runner.manage_and_run_test_playbooks()


# ====================== generate-outputs ====================== #
@main.command(short_help='''Generates outputs (from json or examples).''')
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-c", "--command", help="Specific command name (e.g. xdr-get-incidents)",
    required=False)
@click.option(
    "-j", "--json",
    help="Valid JSON file path. If not specified, the script will wait for user input in the terminal. "
         "The response can be obtained by running the command with `raw-response=true` argument.",
    required=False)
@click.option(
    "-p", "--prefix",
    help="Output prefix like Jira.Ticket, VirusTotal.IP, the base path for the outputs that the "
         "script generates", required=False)
@click.option(
    "-o", "--output",
    help="Output file path, if not specified then will print to stdout",
    required=False)
@click.option(
    "-v", "--verbose", is_flag=True,
    help="Verbose output - mainly for debugging purposes")
@click.option(
    "--ai", is_flag=True,
    help="**Experimental** - Help generate context descriptions via AI transformers (must have a valid AI21 key at ai21.com)")
@click.option(
    "--interactive",
    help="If passed, then for each output field will ask user interactively to enter the "
         "description. By default is interactive mode is disabled. No need to use with --ai (it is already interactive)",
    is_flag=True)
@click.option(
    "-d", "--descriptions",
    help="A JSON or a path to a JSON file, mapping field names to their descriptions. "
         "If not specified, the script prompt the user to input the JSON content.",
    is_flag=True)
@click.option(
    "-i", "--input",
    help="Valid YAML integration file path.",
    required=False)
@click.option(
    "-e", "--examples",
    help="Integrations: path for file containing command examples."
         " Each command should be in a separate line."
         " Scripts: the script example surrounded by quotes."
         " For example: -e '!ConvertFile entry_id=<entry_id>'")
@click.option(
    "--insecure",
    help="Skip certificate validation to run the commands in order to generate the docs.",
    is_flag=True)
def generate_outputs(**kwargs):
    """Demisto integrations/scripts have a YAML file that defines them.
    Creating the YAML file is a tedious and error-prone task of manually copying outputs from the API result to the
    file/UI/PyCharm. This script auto generates the YAML for a command from the JSON result of the relevant API call
    In addition you can supply examples files and generate the context description directly in the YML from those examples.
    """
    from demisto_sdk.commands.generate_outputs.generate_outputs import \
        run_generate_outputs
    check_configuration_file('generate-outputs', kwargs)
    return run_generate_outputs(**kwargs)


# ====================== generate-test-playbook ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input',
    required=True,
    help='Specify integration/script yml path')
@click.option(
    '-o', '--output',
    required=False,
    help='Specify output directory or path to an output yml file. '
         'If a path to a yml file is specified - it will be the output path.\n'
         'If a folder path is specified - a yml output will be saved in the folder.\n'
         'If not specified, and the input is located at `.../Packs/<pack_name>/Integrations`, '
         'the output will be saved under `.../Packs/<pack_name>/TestPlaybooks`.\n'
         'Otherwise (no folder in the input hierarchy is named `Packs`), '
         'the output will be saved in the current directory.')
@click.option(
    '-n', '--name',
    required=True,
    help='Specify test playbook name. The output file name will be `playbook-<name>_Test.yml')
@click.option(
    '--no-outputs', is_flag=True,
    help='Skip generating verification conditions for each output contextPath. Use when you want to decide which '
         'outputs to verify and which not')
@click.option(
    "-v", "--verbose", help="Verbose output for debug purposes - shows full exception stack trace", is_flag=True)
@click.option(
    "-ab", "--all-brands", "use_all_brands",
    help="Generate a test-playbook which calls commands using integrations of all available brands. "
         "When not used, the generated playbook calls commands using instances of the provided integration brand.",
    is_flag=True
)
@click.option(
    "-c", "--commands", help="A comma-separated command names to generate playbook tasks for, "
                             "will ignore the rest of the commands."
                             "e.g xdr-get-incidents,xdr-update-incident",
    required=False
)
@click.option(
    "-e", "--examples", help="For integrations: path for file containing command examples."
                             " Each command should be in a separate line."
                             " For scripts: the script example surrounded by quotes."
                             " For example: -e '!ConvertFile entry_id=<entry_id>'"
)
@click.option(
    "-u", "--upload", help="Whether to upload the test playbook after the generation.", is_flag=True)
def generate_test_playbook(**kwargs):
    """Generate test playbook from integration or script"""
    from demisto_sdk.commands.generate_test_playbook.test_playbook_generator import \
        PlaybookTestsGenerator
    check_configuration_file('generate-test-playbook', kwargs)
    file_type: FileType = find_type(kwargs.get('input', ''), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT]:
        print_error('Generating test playbook is possible only for an Integration or a Script.')
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
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-n", "--name", help="The name of the directory and file you want to create")
@click.option(
    "--id", help="The id used in the yml file of the integration or script"
)
@click.option(
    "-o", "--output", help="The output dir to write the object into. The default one is the current working "
                           "directory.")
@click.option(
    '--integration', is_flag=True, help="Create an Integration based on BaseIntegration template")
@click.option(
    '--script', is_flag=True, help="Create a Script based on BaseScript example")
@click.option(
    "--pack", is_flag=True, help="Create pack and its sub directories")
@click.option(
    "-t", "--template", help="Create an Integration/Script based on a specific template.\n"
                             "Integration template options: HelloWorld, HelloIAMWorld, FeedHelloWorld.\n"
                             "Script template options: HelloWorldScript")
@click.option(
    "-a", "--author-image", help="Path of the file 'Author_image.png'. \n "
    "Image will be presented in marketplace under PUBLISHER section. File should be up to 4kb and dimensions of 120x50"
)
@click.option(
    '--demisto_mock', is_flag=True,
    help="Copy the demistomock. Relevant for initialization of Scripts and Integrations within a Pack.")
@click.option(
    '--common-server', is_flag=True,
    help="Copy the CommonServerPython. Relevant for initialization of Scripts and Integrations within a Pack.")
def init(**kwargs):
    """Initialize a new Pack, Integration or Script.
    If the script/integration flags are not present, we will create a pack with the given name.
    Otherwise when using the flags we will generate a script/integration based on your selection.
    """
    from demisto_sdk.commands.init.initiator import Initiator
    check_configuration_file('init', kwargs)
    initiator = Initiator(**kwargs)
    initiator.init()
    return 0


# ====================== generate-docs ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input", help="Path of the yml file.", required=True)
@click.option(
    "-o", "--output", help="The output dir to write the documentation file into,"
                           " documentation file name is README.md. If not specified, will be in the yml dir.",
    required=False)
@click.option(
    "-uc", "--use_cases", help="For integration - Top use-cases. Number the steps by '*' (i.e. '* foo. * bar.')",
    required=False)
@click.option(
    "-c", "--command", help="A comma-separated command names to generate doc for, will ignore the rest of the commands."
                            "e.g xdr-get-incidents,xdr-update-incident",
    required=False
)
@click.option(
    "-e", "--examples", help="Integrations: path for file containing command examples."
                             " Each command should be in a separate line."
                             " Scripts: the script example surrounded by quotes."
                             " For example: -e '!ConvertFile entry_id=<entry_id>'")
@click.option(
    "-p", "--permissions", type=click.Choice(["none", "general", "per-command"]), help="Permissions needed.",
    required=True, default='none')
@click.option(
    "-cp", "--command-permissions", help="Path for file containing commands permissions"
                                         " Each command permissions should be in a separate line."
                                         " (i.e. '<command-name> Administrator READ-WRITE')", required=False)
@click.option(
    "-l", "--limitations", help="Known limitations. Number the steps by '*' (i.e. '* foo. * bar.')", required=False)
@click.option(
    "--insecure", help="Skip certificate validation to run the commands in order to generate the docs.",
    is_flag=True)
@click.option(
    "-v", "--verbose", is_flag=True, help="Verbose output - mainly for debugging purposes.")
@click.option(
    "--old-version", help="Path of the old integration version yml file.")
@click.option(
    "--skip-breaking-changes", is_flag=True, help="Skip generating of breaking changes section.")
def generate_docs(**kwargs):
    """Generate documentation for integration, playbook or script from yaml file."""
    from demisto_sdk.commands.generate_docs.generate_integration_doc import \
        generate_integration_doc
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import \
        generate_playbook_doc
    from demisto_sdk.commands.generate_docs.generate_script_doc import \
        generate_script_doc
    check_configuration_file('generate-docs', kwargs)
    input_path: str = kwargs.get('input', '')
    output_path = kwargs.get('output')
    command = kwargs.get('command')
    examples: str = kwargs.get('examples', '')
    permissions = kwargs.get('permissions')
    limitations = kwargs.get('limitations')
    insecure: bool = kwargs.get('insecure', False)
    verbose: bool = kwargs.get('verbose', False)
    old_version: str = kwargs.get('old_version', '')
    skip_breaking_changes: bool = kwargs.get('skip_breaking_changes', False)

    # validate inputs
    if input_path and not os.path.isfile(input_path):
        print_error(F'Input file {input_path} was not found.')
        return 1

    if not input_path.lower().endswith('.yml'):
        print_error(F'Input {input_path} is not a valid yml file.')
        return 1

    if output_path and not os.path.isdir(output_path):
        print_error(F'Output directory {output_path} was not found.')
        return 1

    if command:
        if output_path and (not os.path.isfile(os.path.join(output_path, "README.md"))) \
                or (not output_path) \
                and (not os.path.isfile(os.path.join(os.path.dirname(os.path.realpath(input_path)), "README.md"))):
            print_error("The `command` argument must be presented with existing `README.md` docs.")
            return 1

    file_type = find_type(kwargs.get('input', ''), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT, FileType.PLAYBOOK]:
        print_error('File is not an Integration, Script or a Playbook.')
        return 1

    if old_version and not os.path.isfile(old_version):
        print_error(F'Input old version file {old_version} was not found.')
        return 1

    if old_version and not old_version.lower().endswith('.yml'):
        print_error(F'Input old version {old_version} is not a valid yml file.')
        return 1

    print(f'Start generating {file_type.value} documentation...')
    if file_type == FileType.INTEGRATION:
        use_cases = kwargs.get('use_cases')
        command_permissions = kwargs.get('command_permissions')
        return generate_integration_doc(input_path=input_path, output=output_path, use_cases=use_cases,
                                        examples=examples, permissions=permissions,
                                        command_permissions=command_permissions, limitations=limitations,
                                        insecure=insecure, verbose=verbose, command=command,
                                        old_version=old_version,
                                        skip_breaking_changes=skip_breaking_changes)
    elif file_type == FileType.SCRIPT:
        return generate_script_doc(input_path=input_path, output=output_path, examples=examples,
                                   permissions=permissions,
                                   limitations=limitations, insecure=insecure, verbose=verbose)
    elif file_type == FileType.PLAYBOOK:
        return generate_playbook_doc(input_path=input_path, output=output_path, permissions=permissions,
                                     limitations=limitations, verbose=verbose)
    else:
        print_error(f'File type {file_type.value} is not supported.')
        return 1


# ====================== create-id-set ====================== #
@main.command(hidden=True)
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input',
    help='Input file path, the default is the content repo.',
    default=''
)
@click.option(
    "-o", "--output",
    help="Output file path, the default is the Tests directory.",
    default=''
)
@click.option(
    '-fd',
    '--fail-duplicates',
    help="Fails the process if any duplicates are found.",
    is_flag=True
)
@click.option('-mp', '--marketplace', help='The marketplace the id set are created for, that determines which packs are'
                                           ' inserted to the id set, and which items are present in the id set for '
                                           'each pack. Default is the XSOAR marketplace, that has all of the packs ',
              default='xsoar')
def create_id_set(**kwargs):
    """Create the content dependency tree by ids."""
    from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
    from demisto_sdk.commands.find_dependencies.find_dependencies import \
        remove_dependencies_from_id_set

    check_configuration_file('create-id-set', kwargs)
    id_set_creator = IDSetCreator(**kwargs)
    # id_set, excluded_items_by_pack, excluded_items_by_type = id_set_creator.create_id_set()

    with open('/Users/rshalem/dev/demisto/demisto-sdk/demisto_sdk/tests/test_files/create_id_set/id_set_after_manual_removal.json') as id_set_file:
        id_set = json.load(id_set_file)

    excluded_items_by_pack = {'Expanse': {('incidentfield', 'incident_expanseexposuretype'), ('integration', 'Expanse'), ('incidentfield', 'incident_expansebehaviorrule'), ('playbook', 'ExpanseParseRawIncident'), ('incidentfield', 'incident_expanseseverity'), ('incidentfield', 'incident_expanserawjsonevent'), ('script', 'ExpanseParseRawIncident'), ('incidentfield', 'incident_expansebusinessunit'), ('incidenttype', 'Expanse Behavior'), ('incidenttype', 'Expanse Appearance'), ('classifier', '95573d05-345e-43b6-82f1-a5a8ad402e69'), ('playbook', 'Expanse Behavior Severity Update')}, 'ExpanseV2': {('indicatorfield', 'indicator_expansedateadded'), ('incidentfield', 'incident_expansebusinessunits'), ('incidentfield', 'incident_expanseasset'), ('indicatorfield', 'indicator_expanseassettype'), ('playbook', 'Expanse Enrich Cloud Assets'), ('incidentfield', 'incident_expanseissueid'), ('script', 'ExpanseRefreshIssueAssets'), ('incidentfield', 'incident_expanseinitialevidence'), ('incidentfield', 'incident_expansemodified'), ('indicatorfield', 'indicator_expanseprovidername'), ('playbook', 'Expanse Load-Create List'), ('script', 'ExpanseAggregateAttributionUser'), ('incidentfield', 'incident_expanseprogressstatus'), ('incidenttype', 'Expanse Issue'), ('incidenttype', 'Xpanse Issue - Generic'), ('incidentfield', 'incident_expansetags'), ('incidentfield', 'incident_expansemlfeatures'), ('incidentfield', 'incident_expansepriority'), ('incidentfield', 'incident_expansecertificate'), ('incidentfield', 'incident_expansecloudmanagementstatus'), ('indicatorfield', 'indicator_expansefirstobserved'), ('indicatorfield', 'indicator_expansetenantname'), ('incidentfield', 'incident_expanseservice'), ('script', 'MatchIPinCIDRIndicators'), ('incidentfield', 'incident_expanseport'), ('mapper', 'ExpanseV2-mapper'), ('playbook', 'Expanse VM Enrich'), ('incidentfield', 'incident_expanseprovider'), ('playbook', 'Xpanse Incident Handling - Generic'), ('incidentfield', 'incident_expanselatestevidence'), ('incidentfield', 'incident_expansegeolocation'), ('classifier', 'ExpanseV2'), ('playbook', 'Handle Expanse Incident - Attribution Only'), ('incidentfield', 'incident_expanseassetowner'), ('script', 'ExpanseAggregateAttributionIP'), ('script', 'ExpanseAggregateAttributionDevice'), ('playbook', 'NSA - 5 Security Vulnerabilities Under Active Nation-State Attack'), ('script', 'ExpansePrintSuggestions'), ('playbook', 'Extract and Enrich Expanse Indicators'), ('incidentfield', 'incident_expanseactivitystatus'), ('incidentfield', 'incident_expansecreated'), ('playbook', 'Expanse Find Cloud IP Address Region and Service'), ('incidentfield', 'incident_expanseassetorganizationunit'), ('script', 'ExpanseEvidenceDynamicSection'), ('incidentfield', 'incident_expanseip'), ('indicatorfield', 'indicator_expanselastobserved'), ('incidentfield', 'incident_expansecategory'), ('integration', 'ExpanseV2'), ('indicatorfield', 'indicator_expansesourcedomain'), ('indicatorfield', 'indicator_expanseproperties'), ('indicatorfield', 'indicator_expansecertificateadvertisementstatus'), ('incidentfield', 'incident_expanseshadowit'), ('incidentfield', 'incident_expansedomain'), ('incidentfield', 'incident_expanseprotocol'), ('incidentfield', 'incident_expanseregion'), ('integration', 'FeedExpanse'), ('script', 'ExpanseAggregateAttributionCI'), ('indicatorfield', 'indicator_expansetype'), ('indicatorfield', 'indicator_expanseservicestatus'), ('playbook', 'Expanse Unmanaged Cloud'), ('script', 'ExpanseEnrichAttribution'), ('playbook', 'Handle Expanse Incident'), ('playbook', 'Expanse Attribution'), ('script', 'ExpanseGenerateIssueMapWidgetScript'), ('indicatorfield', 'indicator_expansebusinessunits'), ('indicatorfield', 'indicator_expansednsresolutionstatus'), ('incidentfield', 'incident_expanseassignee'), ('incidentfield', 'incident_expanseissuetype'), ('indicatorfield', 'indicator_expansedomain'), ('indicatorfield', 'indicator_expansetags')}, 'Wiz': {('incidentfield', 'incident_wizissueid'), ('incidentfield', 'incident_wizissueduedate'), ('incidentfield', 'incident_wizresourceregion'), ('incidentfield', 'incident_wizcloudplatform'), ('incidentfield', 'incident_wizresourcetype'), ('mapper', 'Wiz Mapper'), ('mapper', 'Wiz Mapper Webhook'), ('incidentfield', 'incident_wizresourceid'), ('incidenttype', 'Wiz Issue'), ('incidentfield', 'incident_wizdetails'), ('integration', 'Wiz'), ('incidentfield', 'incident_wizissuenote'), ('incidentfield', 'incident_wizcloudaccount'), ('incidentfield', 'incident_wizcloudaccountname'), ('classifier', 'Wiz Classifier')}, 'Traps': {('playbook', 'Traps Quarantine Event'), ('playbook', 'Traps Blacklist File'), ('integration', 'Palo Alto Traps ESM (Beta)'), ('playbook', 'Traps Isolate Endpoint'), ('integration', 'Traps'), ('incidenttype', 'Traps'), ('incidentfield', 'incident_trapsid'), ('playbook', 'Traps Scan Endpoint'), ('playbook', 'Traps Retrieve And Download Files')}, 'FeedMandiant': {('indicatorfield', 'indicator_feedmandiantdetections'), ('indicatorfield', 'indicator_feedmandiantreportid'), ('integration', 'FeedMandiant'), ('indicatorfield', 'indicator_feedmandiantversion')}, 'CortexXDR': {('incidentfield', 'incident_xdrusers'), ('playbook', 'Cortex XDR Alerts Handling'), ('incidentfield', 'incident_xdrmodificationtime'), ('incidentfield', 'incident_xdrlowseverityalertcount'), ('playbook', 'Cortex XDR - Execute commands'), ('incidentfield', 'incident_xdrdescription'), ('integration', 'Cortex XDR - IOC'), ('incidentfield', 'incident_xdrnotes'), ('incidentfield', 'incident_xdrmediumseverityalertcount'), ('playbook', 'Cortex XDR - Block File'), ('incidentfield', 'incident_xdrdisconnectedendpoints'), ('incidentfield', 'incident_xdrfilesha256'), ('playbook', 'Cortex XDR - Execute snippet code script'), ('incidentfield', 'incident_xdralertcount'), ('incidentfield', 'incident_xdrfileartifacts'), ('incidentfield', 'incident_lastmirroredintime'), ('incidentfield', 'incident_xdralertname'), ('script', 'EntryWidgetNumberHostsXDR'), ('playbook', 'Cortex XDR - Isolate Endpoint'), ('incidentfield', 'incident_xdrdetectiontime'), ('playbook', 'Cortex XDR - AWS IAM user access investigation'), ('script', 'CortexXDRCloudProviderWidget'), ('incidentfield', 'incident_xdrmitretactics'), ('playbook', 'Cortex XDR - Run script'), ('incidentfield', 'incident_xdrdevicecontrolviolations'), ('mapper', 'Cortex XDR - IR-out-mapper'), ('playbook', 'Cortex XDR - Malware Investigation'), ('incidentfield', 'incident_xdrfilename'), ('incidentfield', 'incident_xdrnetworkartifacts'), ('playbook', 'Cortex XDR disconnected endpoints'), ('playbook', 'Cortex XDR - Check Action Status'), ('script', 'EntryWidgetNumberUsersXDR'), ('script', 'CortexXDRAdditionalAlertInformationWidget'), ('incidentfield', 'incident_xdrmanualseverity'), ('playbook', 'Cortex XDR Incident Handling'), ('script', 'XDRDisconnectedEndpoints'), ('classifier', 'Cortex XDR - IR'), ('incidentfield', 'incident_xdrincidentid'), ('script', 'EntryWidgetPieAlertsXDR'), ('incidenttype', 'Cortex XDR Device Control Violations'), ('incidentfield', 'incident_xdrhighseverityalertcount'), ('playbook', 'Cortex XDR device control violations'), ('playbook', 'Cortex XDR Incident Sync'), ('script', 'DBotGroupXDRIncidents'), ('incidenttype', 'Cortex XDR Disconnected endpoints'), ('integration', 'Cortex XDR - IR'), ('playbook', 'Cortex XDR incident handling v2'), ('indicatorfield', 'indicator_xdrstatus'), ('incidentfield', 'incident_xdrhostcount'), ('incidentfield', 'incident_xdrassigneduseremail'), ('integration', 'Cortex XDR - XQL Query Engine'), ('incidentfield', 'incident_xdrurl'), ('incidentfield', 'incident_xdralertcategory'), ('incidentfield', 'incident_xdrresolvecomment'), ('playbook', 'Cortex XDR incident handling v3'), ('incidentfield', 'incident_xdrassigneduserprettyname'), ('incidentfield', 'incident_xdralerts'), ('playbook', 'Cortex XDR - check file existence'), ('incidenttype', 'Cortex XDR Port Scan'), ('playbook', 'Cortex XDR - Retrieve File Playbook'), ('mapper', 'Cortex XDR - IR-mapper'), ('script', 'CortexXDRIdentityInformationWidget'), ('incidenttype', 'Cortex XDR - XCLOUD'), ('playbook', 'JOB - Cortex XDR query endpoint device control violations'), ('script', 'XDRSyncScript'), ('playbook', 'Cortex XDR - kill process'), ('playbook', 'Cortex XDR - Unisolate Endpoint'), ('playbook', 'Cortex XDR - delete file'), ('playbook', 'Cortex XDR - Port Scan'), ('incidenttype', 'Cortex XDR Incident'), ('incidentfield', 'incident_xdrstatusv2'), ('incidentfield', 'incident_xdrsimilarincidents'), ('playbook', 'Cortex XDR - PrintNightmare Detection and Response'), ('playbook', 'Cortex XDR - Port Scan - Adjusted'), ('incidentfield', 'incident_xdrusercount'), ('incidentfield', 'incident_xdrmitretechniques'), ('classifier', '32f26072-9a69-41a5-8db8-0d1226431078'), ('playbook', 'Cortex XDR - quarantine file'), ('script', 'XDRConnectedEndpoints'), ('script', 'CortexXDRRemediationActionsWidget'), ('incidentfield', 'incident_xdrstatus')}, 'DeprecatedContent': {('script', 'EPOUpdateRepository'), ('playbook', 'search_endpoints_by_hash_-_carbon_black_response'), ('script', 'AwsGetInstanceInfo'), ('script', 'EPORepositoryComplianceCheck'), ('script', 'GoogleappsGmailGetMail'), ('script', 'PWEvents'), ('script', 'BinaryReputationPy'), ('script', 'AwsCreateVolumeSnapshot'), ('script', 'QrFullSearch'), ('script', 'VectraGetHostById'), ('script', 'CYFileRep'), ('integration', 'Mimecast Authentication'), ('script', 'VectraTriage'), ('script', 'VectraSummary'), ('integration', 'AlienVault OTX'), ('script', 'ConferSetSeverity'), ('script', 'ExposeUsers'), ('script', 'NessusGetReport'), ('script', 'TaniumAskQuestion'), ('integration', 'WildFire'), ('script', 'SNUpdateTicket'), ('integration', 'Intezer'), ('script', 'QrGetSearchResults'), ('script', 'getMlFeatures'), ('script', 'QrGetSearch'), ('integration', 'SafeBreach'), ('script', 'DataURLReputation'), ('script', 'DefaultIncidentClassifier'), ('script', 'GoogleappsListUsers'), ('integration', 'Phishme Intelligence'), ('script', '7b02fa0f-94ff-48c7-8350-b4e353702e73'), ('playbook', 'dedup_incidents_-_ml'), ('script', 'ADGetGroupUsers'), ('script', 'TaniumDeployAction'), ('script', 'da330ce7-3a93-430c-8454-03b96cf5184e'), ('script', 'IncidentSet'), ('playbook', 'playbook11'), ('script', 'NessusScanDetails'), ('script', 'ADGetCommonGroups'), ('playbook', 'entity_enrichment_generic'), ('script', 'LCMPathFinderScanHost'), ('playbook', 'vulnerability_handling_-_qualys_-_add _ustom_fields_to_default_layout'), ('script', 'ADGetUsersByEmail'), ('integration', 'Lockpath KeyLight'), ('script', 'AwsCreateImage'), ('script', 'IPExtract'), ('integration', 'Amazon Web Services'), ('script', 'PWObservations'), ('playbook', 'Account Enrichment - Generic v2'), ('script', 'PanoramaBlockIP'), ('script', 'LCMSetHostComment'), ('script', 'a6e348f4-1e40-4365-870c-52139c60779a'), ('script', 'NessusScanStatus'), ('script', 'SlackSend'), ('script', 'SplunkEmailParser'), ('script', 'PWSensors'), ('playbook', 'Process Email'), ('script', 'AwsStopInstance'), ('script', 'NessusCreateScan'), ('playbook', 'PANW - Hunting and threat detection by indicator type'), ('script', 'WhoisSummary'), ('script', 'XBLockouts'), ('script', 'ADGetComputer'), ('script', 'ExposeList'), ('playbook', 'playbook13'), ('script', 'CSActors'), ('script', 'CPShowAccessRulebase'), ('script', 'TaniumAskQuestionComplex'), ('script', 'ADGetEmailForAllUsers'), ('script', 'PanoramaConfig'), ('script', 'ClassifierNotifyAdmin'), ('playbook', 'File Enrichment - Generic'), ('playbook', 'block_indicators_-_generic'), ('script', 'AwsStartInstance'), ('script', 'GetDuplicatesMl'), ('playbook', 'email_address_enrichment_-_generic'), ('script', '10cb3486-48f3-4d93-88af-b6be84ffd432'), ('playbook', 'Calculate Severity - Generic'), ('script', 'EPORepoList'), ('playbook', 'PANW - Hunting and threat detection by indicator type V2'), ('playbook', 'Email Address Enrichment - Generic v2'), ('script', 'dbbdc2e4-6105-4ee9-8e83-563a4b991a89'), ('playbook', 'Failed Login Playbook With Slack'), ('script', 'ADListUsersEx'), ('integration', 'ArcSight ESM'), ('playbook', 'Account Enrichment'), ('script', 'RunSqlQuery'), ('integration', 'Azure Compute'), ('script', '82764532-0a4f-4b59-8cf9-fe1a00cabdae'), ('script', 'MD5Extract'), ('script', 'ExchangeDeleteIDsFromContext'), ('integration', 'jira'), ('playbook', 'malware_investigation-_generic'), ('script', 'ConferIncidentDetails'), ('script', 'CheckURLs'), ('integration', 'Azure Security Center'), ('playbook', 'dedup_-_generic'), ('script', 'NetwitnessSAUpdateIncident'), ('integration', 'Proofpoint TAP'), ('script', 'ExtractEmail'), ('script', '2aa9f737-8c7c-42f5-815f-4d104bb3af06'), ('script', 'AwsRunInstance'), ('integration', 'OPSWAT-Metadefender'), ('script', 'SendEmail'), ('script', 'VectraSettings'), ('playbook', 'playbook12'), ('script', 'GoogleappsRevokeUserRole'), ('playbook', 'ExtraHop - Ticket Tracking'), ('script', 'CBFindHash'), ('playbook', 'add_indicator_to_miner_-_palo_alto_mineMeld'), ('script', 'ADGetComputerGroups'), ('classifier', '5c83f473-c618-4c41-85d8-251eb1f90566'), ('playbook', 'Enrich McAfee DXL using 3rd party sandbox'), ('playbook', 'Hunt for bad IOCs'), ('script', 'GoogleappsGmailSearch'), ('script', 'GetContextValue'), ('script', 'CloseInvestigation'), ('script', 'ParseEmailHeader'), ('script', 'TaniumApprovePendingActions'), ('playbook', 'calculate_severity_-_critical_assets'), ('script', 'ADGetUserGroups'), ('script', 'ADIsUserMember'), ('script', 'NessusHostDetails'), ('playbook', 'QRadar - Get offense correlations '), ('script', 'XBUser'), ('script', '80b5c44c-4eac-4e00-812f-6d409d57be31'), ('script', 'SplunkSearchJsonPy'), ('playbook', 'get_file_sample_by_hash_-_generic'), ('playbook', 'Endpoint data collection'), ('script', 'WildfireUpload'), ('script', 'ReadPDFFile'), ('script', 'CPCreateBackup'), ('integration', 'EWS'), ('playbook', 'Failed Login Playbook - Slack v2'), ('script', 'JiraCreateIssue'), ('script', 'CPDeleteRule'), ('playbook', 'Get Mails By Folder Pathes'), ('integration', 'Symantec Endpoint Protection'), ('script', 'LocateAttachment'), ('playbook', 'playbook16'), ('script', 'SNOpenTicket'), ('script', 'BlockIP'), ('script', 'CPBlockIP'), ('script', 'DocumentationAutomation'), ('script', 'DataHashReputation'), ('script', 'ExtractIP'), ('playbook', 'block_ip_-_generic'), ('script', '9364c36f-b1d6-4233-88c2-75008b106c31'), ('playbook', 'vulnerability_handling_-_qualys'), ('script', 'ExtractDomainFromURL'), ('script', 'LCMIndicatorsForEntity'), ('script', 'DBotPredictPhishingEvaluation'), ('script', 'IsContextSet'), ('script', 'CSHuntByIOC'), ('playbook', 'url_enrichment_-_generic'), ('script', 'ExtractURL'), ('script', 'DBotPreparePhishingData'), ('script', 'TaniumFindRunningProcesses'), ('script', 'SetIncidentCustomFields'), ('integration', 'Kenna'), ('playbook', 'PanoramaQueryTrafficLogs'), ('script', 'IPInfoQuery'), ('script', 'LCMAcknowledgeHost'), ('script', 'VectraGetDetetctionsById'), ('script', 'CommonIntegrationPython'), ('script', 'LCMDetectedIndicators'), ('script', 'GoogleappsGetUserRoles'), ('script', 'PanoramaDynamicAddressGroup'), ('script', 'SNListTickets'), ('script', 'EPODetermineRepository'), ('script', 'GoogleappsGetUser'), ('script', 'EsmExample'), ('script', 'f99a85a6-c572-4c3a-8afd-5b4ac539000a'), ('script', 'ADGetGroupMembers'), ('script', 'LCMResolveHost'), ('script', 'CPTaskStatus'), ('playbook', 'PAN-OS EDL Setup v2'), ('script', 'PanoramaPcaps'), ('integration', 'Pwned'), ('script', 'DataDomainReputation'), ('integration', 'Palo Alto Networks Cortex'), ('script', 'ADListUsers'), ('playbook', 'malware_investigation-_generic_-_setup'), ('script', 'AdSearch'), ('playbook', 'Carbon Black Rapid IOC Hunting'), ('playbook', 'ip_enrichment_generic'), ('script', 'CBSearch'), ('playbook', 'PAN-OS EDL Setup'), ('integration', 'Cylance Protect'), ('script', 'ExchangeAssignRole'), ('script', 'CPSetRule'), ('playbook', 'endpoint_enrichment_-_generic'), ('script', 'SandboxDetonateFile'), ('script', 'PWObservationDetails'), ('integration', 'PostgreSQL'), ('script', 'XBNotable'), ('integration', 'Shodan'), ('script', 'CheckFiles'), ('script', 'GoogleAuthURL'), ('script', 'URLExtract'), ('script', 'VectraHealth'), ('script', 'CheckWhitelist'), ('playbook', 'Endpoint Enrichment - Generic v2'), ('script', 'TaniumShowPendingActions'), ('script', 'QrOffenses'), ('script', 'NessusListScans'), ('integration', 'Palo Alto Minemeld'), ('script', 'ADGetAllUsersEmail'), ('playbook', 'PanoramaCommitConfiguration'), ('script', 'InviteUser'), ('script', 'CSIndicators'), ('script', '840aa9a7-04b2-4505-8238-8fe85f010dde'), ('script', 'ADListComputers'), ('script', 'ExtractDomain'), ('script', '3dd62013-4fed-43eb-8ae4-91b1b4250599'), ('script', 'SetSeverityByScore'), ('script', 'SplunkSearch'), ('script', 'ExtractHash'), ('playbook', 'close_incident_if_duplicate_found'), ('playbook', 'PAN-OS - Block IP and URL - External Dynamic List'), ('script', 'DemistoDeleteIncident'), ('script', 'SlackMirror'), ('playbook', 'process_email_-_add_custom_fields'), ('script', 'AggregateIOCs'), ('script', 'JiraIssueUploadFile'), ('integration', 'Secdo'), ('playbook', 'Demisto_Self-Defense_-_Account_policy_monitoring_playbook'), ('script', 'PWEventDetails'), ('script', 'ElasticSearchDisplay'), ('playbook', 'playbook10'), ('script', 'WildfireReport'), ('script', 'JiraIssueAddComment'), ('script', 'CSCountDevicesForIOC'), ('script', 'VectraDetections'), ('script', 'NessusLaunchScan'), ('playbook', 'DBotCreatePhishingClassifierJob'), ('playbook', 'Enrichment Playbook'), ('script', 'PWEventPcapInfo'), ('script', 'JiraIssueAddLink'), ('script', 'IncidentToContext'), ('playbook', 'account_enrichment_-_generic'), ('script', 'DBotTrainTextClassifier'), ('script', 'JiraIssueQuery'), ('playbook', 'Enrich DXL with ATD verdict'), ('playbook', 'block_file_-_generic'), ('script', 'Elasticsearch'), ('script', 'EPOUpdateEndpoints'), ('playbook', 'playbook5'), ('script', 'XBTriggeredRules'), ('script', 'NessusShowEditorTemplates'), ('playbook', 'DBotCreatePhishingClassifier'), ('script', 'SlackAskUser'), ('script', 'ExchangeDeleteMail'), ('script', 'XBTimeline'), ('integration', 'ExtraHop'), ('script', 'CPShowBackupStatus'), ('script', 'ADGetGroupComputers'), ('script', 'ProofpointDecodeURL'), ('script', 'VectraClassifier'), ('script', 'PWFindEvents'), ('integration', 'Mimecast'), ('integration', 'MISP'), ('script', 'ADSetNewPassword'), ('integration', 'Lastline'), ('script', 'ADGetEmailForUser'), ('playbook', 'search_endpoints_by_hash_-_generic'), ('script', 'IngestCSV'), ('playbook', 'playbook14'), ('script', '7b5c080e-f3b1-411a-83b0-e1f53c21bef8'), ('script', '94f72ed9-49c8-40e5-89bb-7c98f914d2cc'), ('integration', 'LightCyber Magna'), ('script', 'JiraGetIssue'), ('script', 'CommonIntegration'), ('playbook', 'extract_indicators_from_file_-_generic'), ('script', 'DBotPredictTextLabel'), ('script', '514ec833-c02c-49a3-8ac6-d982198f5fa0'), ('integration', 'Cymon'), ('script', 'ADUserLogonInfo'), ('integration', 'CVE Search'), ('script', 'CheckIPs'), ('script', 'ExposeModules'), ('playbook', 'domain_enrichment_generic'), ('script', 'EPOCheckLatestDAT'), ('script', 'ExchangeSearchMailbox'), ('playbook', 'Incident Enrichment'), ('script', 'ADExpirePassword'), ('playbook', 'playbook1'), ('script', 'PanoramaCommit'), ('playbook', 'Hunt Extracted Hashes'), ('script', 'XBInfo'), ('script', 'ParseEmailFile'), ('script', 'CPShowHosts'), ('script', 'PanoramaMove'), ('script', 'HTMLDocsAutomation'), ('playbook', 'Palo Alto Networks - Endpoint Malware Investigation v2'), ('script', 'DBotPredictPhishingLabel'), ('script', 'LCMDetectedEntities'), ('script', 'LCMHosts'), ('playbook', 'extract_indicators_-_generic'), ('script', 'VectraHosts'), ('script', 'EPORetrieveCurrentDATVersion'), ('script', 'SearchIncidents'), ('script', 'CheckFilesWildfirePy'), ('script', 'IsIPInSubnet'), ('script', 'DataIPReputation'), ('script', 'QrSearches'), ('playbook', 'playbook7'), ('script', 'ExchangeSearch'), ('script', 'VectraSensors'), ('playbook', 'Phishing Investigation - Generic'), ('script', 'PWObservationPcapInfo'), ('script', 'TriagePhishing')}, 'Inventa': {('incidentfield', 'incident_inventadsardatabases'), ('incidentfield', 'incident_inventadsarpiientities'), ('incidentfield', 'incident_inventadsarinventaticket'), ('incidentfield', 'incident_inventapassportnumber'), ('incidentfield', 'incident_inventavehiclenumber'), ('incidentfield', 'incident_inventacreditcardnumber'), ('incidentfield', 'incident_inventadsarfiles'), ('incidentfield', 'incident_inventadsartransactions'), ('incidentfield', 'incident_inventadsardatasubjectid'), ('incidentfield', 'incident_inventapiientities'), ('integration', 'Inventa'), ('incidentfield', 'incident_inventareportreason'), ('incidentfield', 'incident_inventadsardatasubjectemail'), ('incidentfield', 'incident_inventadsardatasubjectname'), ('incidentfield', 'incident_inventataxid'), ('playbook', 'DSAR Inventa Handler'), ('incidenttype', 'iDSAR'), ('incidentfield', 'incident_inventanationalid'), ('incidentfield', 'incident_inventadriverlicense'), ('incidentfield', 'incident_inventafullname'), ('incidentfield', 'incident_inventadsardataassets'), ('incidentfield', 'incident_inventabirthday')}, 'NetskopeV2': {('integration', 'Netskope (API v2)')}, 'CrowdStrikeFalconStreamingV2': {('integration', 'CrowdStrike Falcon Streaming v2'), ('script', 'CrowdStrikeStreamingPreProcessing'), ('classifier', '5d9a5ec5-33cb-4f82-8c5e-e8ae6f7831d8'), ('mapper', 'crowdstrike-streaming-api-mapper'), ('classifier', 'crowdstrike-streaming-api')}, 'qualys': {('playbook', 'Vulnerability Management - Qualys (Job) - V2'), ('playbook', 'vulnerability_management_-_qualys_Job')}, 'IntegrationsAndIncidentsHealthCheck': {('script', 'IncidentsCheck-NumberofIncidentsNoOwner'), ('incidentfield', 'incident_playbooktaskserrors'), ('script', 'IntegrationsCheck-Widget-NumberFailingInstances'), ('script', 'IncidentsCheck-Widget-CommandsNames'), ('incidentfield', 'incident_createddatefailedincidents'), ('incidentfield', 'incident_numberoffailedincidents'), ('incidentfield', 'incident_integrationsfailedcategories'), ('script', 'RestartFailedTasks'), ('playbook', 'JOB - Integrations and Playbooks Health Check'), ('script', 'IncidentsCheck-Widget-NumberofErrors'), ('incidentfield', 'incident_playbooksfailedcommands'), ('incidentfield', 'incident_playbooknameswithfailedtasks'), ('script', 'InstancesCheck-NumberofEnabledInstances'), ('playbook', 'JOB - Integrations and Playbooks Health Check - Lists handling'), ('playbook', 'Integrations and Playbooks Health Check - Running Scripts'), ('script', 'IncidentsCheck-Widget-CreationDate'), ('incidenttype', 'Integrations and Incidents Health Check'), ('script', 'IncidentsCheck-NumberofTotalEntriesErrors'), ('script', 'IntegrationsCheck-Widget-IntegrationsCategory'), ('incidentfield', 'incident_totalinstances'), ('script', 'IncidentsCheck-PlaybooksHealthNames'), ('script', 'IncidentsCheck-Widget-IncidentsErrorsInfo'), ('incidentfield', 'incident_failedincidentscreateddate'), ('script', 'IntegrationsCheck-Widget-NumberChecked'), ('script', 'IncidentsCheck-Widget-UnassignedFailingIncidents'), ('incidentfield', 'incident_integrationscategories'), ('script', 'IntegrationsCheck-Widget-IntegrationsErrorsInfo'), ('script', 'InstancesCheck-NumberofFailedInstances'), ('script', 'InstancesCheck-FailedCategories'), ('script', 'CopyLinkedAnalystNotes'), ('incidentfield', 'incident_totalfailedinstances'), ('incidentfield', 'incident_playbookswithfailedtasks'), ('script', 'IncidentsCheck-Widget-NumberFailingIncidents'), ('script', 'IncidentsCheck-NumberofIncidentsWithErrors'), ('script', 'IncidentsCheck-PlaybooksFailingCommands'), ('script', 'GetFailedTasks'), ('incidentfield', 'incident_unassignedincidents'), ('incidentfield', 'incident_totalgoodinstances'), ('incidentfield', 'incident_numberofentriesiderrors'), ('incidentfield', 'incident_integrationstestgrid'), ('script', 'IncidentsCheck-Widget-PlaybookNames'), ('incidentfield', 'incident_similarincident')}, 'AnsibleTower': {('playbook', 'Launch Job - Ansible Tower')}, 'FortiSandbox': {('playbook', 'FortiSandbox - Loop for Job Submissions'), ('playbook', 'FortiSandbox - Loop For Job Verdict')}, 'CommonPlaybooks': {('playbook', 'Send Investigation Summary Reports Job')}, 'TIM_SIEM': {('playbook', 'TIM - Add Url Indicators To SIEM'), ('playbook', 'TIM - Add Bad Hash Indicators To SIEM'), ('playbook', 'TIM - Add All Indicator Types To SIEM'), ('playbook', 'TIM - Add IP Indicators To SIEM'), ('playbook', 'TIM - Add Domain Indicators To SIEM')}, 'ShiftManagement': {('script', 'GetUsersOnCall'), ('incidentfield', 'incident_shiftopenincidents'), ('script', 'GetOnCallHoursPerUser'), ('script', 'CreateChannelWrapper'), ('script', 'AssignAnalystToIncidentOOO'), ('incidentfield', 'incident_tostartthemeeting'), ('script', 'OutOfOfficeListCleanup'), ('incidentfield', 'incident_outofftheoffice'), ('script', 'GetNumberOfUsersOnCall'), ('script', 'GetAwayUsers'), ('script', 'AssignToNextShiftOOO'), ('script', 'GetUsersOOO'), ('incidentfield', 'incident_shiftmanagerbriefing'), ('playbook', 'Assign Active Incidents to Next Shift V2'), ('incidentfield', 'incident_tojointhemeeting'), ('playbook', 'Set up a Shift handover meeting'), ('script', 'TimeToNextShift'), ('script', 'ManageOOOusers'), ('script', 'GetRolesPerShift'), ('playbook', 'Shift handover'), ('script', 'GetShiftsPerUser'), ('incidenttype', 'Shift handover')}, 'PANOStoCDLMonitoring': {('playbook', 'PAN-OS to Cortex Data Lake Monitoring - Cron Job')}, 'EmployeeOffboarding': {('incidentfield', 'incident_googleadminrolesstatus'), ('incidentfield', 'incident_mailboxdelegation'), ('incidentfield', 'incident_devicegsuiteaccountstatus'), ('playbook', 'Employee Offboarding - Retain & Delete'), ('playbook', 'IT - Employee Offboarding - Manual'), ('incidentfield', 'incident_duoaccountstatus'), ('incidentfield', 'incident_activedirectorydisplayname'), ('incidentfield', 'incident_googledrivestatus'), ('incidentfield', 'incident_globaldirectoryvisibility'), ('incidentfield', 'incident_offboardingstage'), ('incidentfield', 'incident_activedirectorypasswordstatus'), ('incidentfield', 'incident_companypropertystatus'), ('incidentfield', 'incident_emailautoreply'), ('playbook', 'IT - Employee Offboarding'), ('incidentfield', 'incident_googledisplayname'), ('incidentfield', 'incident_oktaaccountstatus'), ('playbook', 'Employee Offboarding - Revoke Permissions'), ('playbook', 'Employee Offboarding - Delegate'), ('incidentfield', 'incident_activedirectoryaccountstatus'), ('incidentfield', 'incident_googleaccountstatus'), ('incidentfield', 'incident_googlepasswordstatus'), ('incidenttype', 'Employee Offboarding'), ('incidentfield', 'incident_googlemailstatus'), ('playbook', 'Employee Offboarding - Gather User Information'), ('incidentfield', 'incident_offboardingdate')}, 'Rapid7_Nexpose': {('playbook', 'vulnerability_management_-_nexpose_job')}, 'ML': {('playbook', 'DBot Create Phishing Classifier V2 Job')}, 'XSOAR-SimpleDevToProd': {('playbook', 'JOB - XSOAR - Export Selected Custom Content'), ('playbook', 'JOB - XSOAR - Simple Dev to Prod')}, 'Campaign': {('script', 'ShowCampaignUniqueRecipients'), ('script', 'ShowNumberOfCampaignIncidents'), ('script', 'ShowCampaignHighestSeverity'), ('script', 'GetSendEmailInstances'), ('incidentfield', 'incident_campaignemailsenderinstance'), ('script', 'ShowCampaignSenders'), ('script', 'PerformActionOnCampaignIncidents'), ('playbook', 'Detect & Manage Phishing Campaigns'), ('script', 'SendEmailToCampaignRecipients'), ('script', 'ShowCampaignRecipients'), ('script', 'GetCampaignDuration'), ('script', 'SplitCampaignContext'), ('script', 'SetPhishingCampaignDetails'), ('script', 'GetCampaignIncidentsIdsAsOptions'), ('incidentfield', 'incident_campaignclosenotes'), ('incidentfield', 'incident_selectaction'), ('script', 'ShowCampaignSimilarityRange'), ('script', 'GetCampaignLowSimilarityIncidentsInfo'), ('incidentfield', 'incident_selectcampaignincidents'), ('script', 'GetCampaignIndicatorsByIncidentId'), ('incidentfield', 'incident_campaignmutualindicators'), ('incidentfield', 'incident_actionsonlowsimilarityincidents'), ('incidentfield', 'incident_actionsoncampaignincidents'), ('incidentfield', 'incident_selectlowsimilarityincidents'), ('script', 'ShowCampaignIncidentsOwners'), ('incidentfield', 'incident_campaignemailsubject'), ('incidenttype', 'Phishing Campaign'), ('script', 'CollectCampaignRecipients'), ('script', 'ShowCampaignUniqueSenders'), ('script', 'ShowCampaignLastIncidentOccurred'), ('incidentfield', 'incident_campaignemailbody'), ('incidentfield', 'incident_incidentsinfo'), ('script', 'GetCampaignLowerSimilarityIncidentsIdsAsOptions'), ('script', 'GetCampaignIncidentsInfo'), ('incidentfield', 'incident_campaignemailto'), ('script', 'IsIncidentPartOfCampaign'), ('script', 'FindEmailCampaign')}, 'PopularCybersecurityNews': {('playbook', 'JOB - Popular News')}, 'TIM_Processing': {('playbook', 'TIM - Update Indicators Organizational External IP Tag'), ('playbook', 'TIM - Process File Indicators With File Hash Type'), ('playbook', 'TIM - Run Enrichment For Domain Indicators'), ('incidenttype', 'Review Indicators Manually'), ('playbook', 'TIM - Indicators Exclusion By Related Incidents'), ('playbook', 'TIM - Process CIDR Indicators By Size'), ('playbook', 'TIM - Review Indicators Manually'), ('incidenttype', 'Review Indicators Manually For Whitelisting'), ('playbook', 'TIM - Run Enrichment For All Indicator Types'), ('playbook', 'TIM - Process Indicators Against Organizations External IP List'), ('playbook', 'TIM - Run Enrichment For Url Indicators'), ('playbook', 'TIM - Run Enrichment For IP Indicators'), ('playbook', 'TIM - Process Indicators - Manual Review'), ('playbook', 'TIM - Process Indicators Against Business Partners Domains List'), ('playbook', 'TIM - Process Indicators - Fully Automated'), ('playbook', 'TIM - Process Indicators Against Business Partners URL List'), ('playbook', 'TIM - Indicator Auto Processing'), ('playbook', 'TIM - Run Enrichment For Hash Indicators'), ('playbook', 'TIM - Review Indicators Manually For Whitelisting'), ('playbook', 'TIM - Process Indicators Against Business Partners IP List'), ('playbook', 'TIM - Process Indicators Against Approved Hash List')}, 'ContentManagement': {('script', 'JobCreator')}, 'ThreatIntelReports': {('script', 'UnpublishThreatIntelReport'), ('script', 'PublishThreatIntelReport')}, 'CommonWidgets': {('script', 'GetLargestInvestigations'), ('script', 'MyToDoTasksWidget'), ('script', 'RSSWidget'), ('script', 'GetLargestInputsAndOuputsInIncidents'), ('script', 'FeedIntegrationErrorWidget')}, 'EmailCommunication': {('mapper', 'MS Graph Mail Single User - Incoming Mapper - Email Communication'), ('classifier', '173a8bc5-663b-4478-89a5-d2ce2ce8a31f'), ('classifier', '0cc88f85-97b7-452e-839c-b58daf0bcf8d'), ('incidentfield', 'incident_emailgeneratedcode'), ('classifier', 'faa1bfc8-37cd-44e0-81fe-73092e381563'), ('classifier', '83d66f08-42b4-4ca6-8145-99bcf7c6b8e5'), ('incidenttype', 'Email Communication'), ('classifier', '18a9fa04-f6e5-43cc-8427-a2ac0d94a8a2'), ('classifier', '6f81fb48-73d0-4f7f-8d3e-9c586ecec38a'), ('script', 'DisplayEmailHtml'), ('incidentfield', 'incident_addcctoemail'), ('mapper', '4f31271a-c22a-4615-862d-2e315778676e'), ('mapper', 'e92f424d-51f4-4d7c-8e35-502f2a4dac02'), ('script', 'SendEmailReply'), ('script', 'PreprocessEmail'), ('classifier', 'MS Graph Mail Single User - Classifier - Email Communication'), ('classifier', 'faa1bfc8-09cd-44e0-81fe-73092e735916'), ('mapper', 'fd0fde44-a619-4273-8c70-569f6620d759')}, 'IAM-SCIM': {('mapper', 'User Profile - SCIM (Incoming)'), ('mapper', 'User Profile - SCIM (Outgoing)')}}
    excluded_items_by_type = {'integration': {'Azure Compute', 'Proofpoint TAP', 'Wiz', 'CVE Search', 'Inventa', 'Lockpath KeyLight', 'FeedMandiant', 'Kenna', 'Cortex XDR - XQL Query Engine', 'Mimecast Authentication', 'Lastline', 'Cylance Protect', 'Cortex XDR - IOC', 'AlienVault OTX', 'SafeBreach', 'WildFire', 'Traps', 'MISP', 'Netskope (API v2)', 'PostgreSQL', 'Amazon Web Services', 'Phishme Intelligence', 'Pwned', 'Azure Security Center', 'Shodan', 'jira', 'Cortex XDR - IR', 'Palo Alto Networks Cortex', 'Symantec Endpoint Protection', 'Secdo', 'LightCyber Magna', 'Expanse', 'ExpanseV2', 'Intezer', 'Palo Alto Traps ESM (Beta)', 'ArcSight ESM', 'FeedExpanse', 'Cymon', 'ExtraHop', 'OPSWAT-Metadefender', 'CrowdStrike Falcon Streaming v2', 'Palo Alto Minemeld', 'Mimecast', 'EWS'}, 'playbook': {'Cortex XDR - kill process', 'calculate_severity_-_critical_assets', 'Cortex XDR incident handling v2', 'Incident Enrichment', 'domain_enrichment_generic', 'TIM - Process Indicators - Manual Review', 'Expanse Find Cloud IP Address Region and Service', 'Cortex XDR - AWS IAM user access investigation', 'Cortex XDR device control violations', 'malware_investigation-_generic_-_setup', 'TIM - Indicators Exclusion By Related Incidents', 'DBot Create Phishing Classifier V2 Job', 'ip_enrichment_generic', 'Cortex XDR - PrintNightmare Detection and Response', 'Cortex XDR - Retrieve File Playbook', 'Cortex XDR Incident Handling', 'DBotCreatePhishingClassifier', 'dedup_-_generic', 'entity_enrichment_generic', 'playbook5', 'FortiSandbox - Loop For Job Verdict', 'TIM - Add All Indicator Types To SIEM', 'Employee Offboarding - Retain & Delete', 'DSAR Inventa Handler', 'Traps Quarantine Event', 'JOB - Cortex XDR query endpoint device control violations', 'vulnerability_handling_-_qualys', 'Enrich McAfee DXL using 3rd party sandbox', 'playbook13', 'Cortex XDR - Port Scan - Adjusted', 'TIM - Process Indicators Against Business Partners IP List', 'Shift handover', 'Handle Expanse Incident', 'playbook7', 'Cortex XDR disconnected endpoints', 'Enrichment Playbook', 'PAN-OS - Block IP and URL - External Dynamic List', 'JOB - Popular News', 'extract_indicators_from_file_-_generic', 'search_endpoints_by_hash_-_generic', 'search_endpoints_by_hash_-_carbon_black_response', 'Cortex XDR - Unisolate Endpoint', 'TIM - Review Indicators Manually', 'Cortex XDR incident handling v3', 'NSA - 5 Security Vulnerabilities Under Active Nation-State Attack', 'TIM - Add Url Indicators To SIEM', 'FortiSandbox - Loop for Job Submissions', 'Hunt Extracted Hashes', 'add_indicator_to_miner_-_palo_alto_mineMeld', 'Expanse Behavior Severity Update', 'malware_investigation-_generic', 'Hunt for bad IOCs', 'Failed Login Playbook - Slack v2', 'TIM - Review Indicators Manually For Whitelisting', 'Cortex XDR - check file existence', 'block_ip_-_generic', 'Failed Login Playbook With Slack', 'close_incident_if_duplicate_found', 'TIM - Process Indicators Against Business Partners URL List', 'playbook11', 'get_file_sample_by_hash_-_generic', 'Cortex XDR - Port Scan', 'Vulnerability Management - Qualys (Job) - V2', 'Process Email', 'block_indicators_-_generic', 'TIM - Process File Indicators With File Hash Type', 'TIM - Process Indicators Against Approved Hash List', 'ExpanseParseRawIncident', 'Traps Retrieve And Download Files', 'vulnerability_management_-_nexpose_job', 'Cortex XDR Incident Sync', 'TIM - Run Enrichment For All Indicator Types', 'TIM - Process Indicators - Fully Automated', 'Cortex XDR Alerts Handling', 'vulnerability_handling_-_qualys_-_add _ustom_fields_to_default_layout', 'Cortex XDR - Malware Investigation', 'TIM - Process CIDR Indicators By Size', 'PanoramaQueryTrafficLogs', 'Send Investigation Summary Reports Job', 'Palo Alto Networks - Endpoint Malware Investigation v2', 'Cortex XDR - Block File', 'Traps Isolate Endpoint', 'Employee Offboarding - Delegate', 'Cortex XDR - Isolate Endpoint', 'PAN-OS EDL Setup', 'DBotCreatePhishingClassifierJob', 'Email Address Enrichment - Generic v2', 'Extract and Enrich Expanse Indicators', 'ExtraHop - Ticket Tracking', 'TIM - Process Indicators Against Organizations External IP List', 'Phishing Investigation - Generic', 'email_address_enrichment_-_generic', 'playbook1', 'process_email_-_add_custom_fields', 'PAN-OS to Cortex Data Lake Monitoring - Cron Job', 'Demisto_Self-Defense_-_Account_policy_monitoring_playbook', 'account_enrichment_-_generic', 'playbook14', 'JOB - XSOAR - Simple Dev to Prod', 'Employee Offboarding - Gather User Information', 'dedup_incidents_-_ml', 'url_enrichment_-_generic', 'IT - Employee Offboarding - Manual', 'TIM - Indicator Auto Processing', 'TIM - Add IP Indicators To SIEM', 'Cortex XDR - Check Action Status', 'Account Enrichment', 'JOB - XSOAR - Export Selected Custom Content', 'Set up a Shift handover meeting', 'TIM - Run Enrichment For IP Indicators', 'Traps Blacklist File', 'playbook10', 'Cortex XDR - Execute snippet code script', 'Launch Job - Ansible Tower', 'TIM - Run Enrichment For Url Indicators', 'Account Enrichment - Generic v2', 'playbook12', 'Cortex XDR - Run script', 'TIM - Add Domain Indicators To SIEM', 'PanoramaCommitConfiguration', 'PANW - Hunting and threat detection by indicator type', 'Expanse Enrich Cloud Assets', 'TIM - Update Indicators Organizational External IP Tag', 'Employee Offboarding - Revoke Permissions', 'extract_indicators_-_generic', 'File Enrichment - Generic', 'TIM - Process Indicators Against Business Partners Domains List', 'Get Mails By Folder Pathes', 'Xpanse Incident Handling - Generic', 'vulnerability_management_-_qualys_Job', 'Cortex XDR - quarantine file', 'TIM - Add Bad Hash Indicators To SIEM', 'PAN-OS EDL Setup v2', 'Expanse VM Enrich', 'Traps Scan Endpoint', 'Carbon Black Rapid IOC Hunting', 'PANW - Hunting and threat detection by indicator type V2', 'Expanse Load-Create List', 'TIM - Run Enrichment For Domain Indicators', 'TIM - Run Enrichment For Hash Indicators', 'Expanse Unmanaged Cloud', 'Expanse Attribution', 'Calculate Severity - Generic', 'Enrich DXL with ATD verdict', 'Handle Expanse Incident - Attribution Only', 'Cortex XDR - delete file', 'Endpoint Enrichment - Generic v2', 'JOB - Integrations and Playbooks Health Check', 'IT - Employee Offboarding', 'Detect & Manage Phishing Campaigns', 'JOB - Integrations and Playbooks Health Check - Lists handling', 'Assign Active Incidents to Next Shift V2', 'QRadar - Get offense correlations ', 'endpoint_enrichment_-_generic', 'Endpoint data collection', 'playbook16', 'block_file_-_generic', 'Integrations and Playbooks Health Check - Running Scripts', 'Cortex XDR - Execute commands'}, 'script': {'GetCampaignLowSimilarityIncidentsInfo', 'NessusLaunchScan', 'CPTaskStatus', 'SlackAskUser', 'VectraHosts', 'SendEmail', 'ADGetEmailForAllUsers', 'CortexXDRRemediationActionsWidget', 'PerformActionOnCampaignIncidents', 'ExtractHash', 'VectraTriage', 'SlackSend', 'IncidentsCheck-Widget-NumberFailingIncidents', 'CheckURLs', 'DemistoDeleteIncident', 'CommonIntegrationPython', 'getMlFeatures', 'GetLargestInvestigations', 'IntegrationsCheck-Widget-NumberFailingInstances', 'NessusListScans', 'ExchangeDeleteIDsFromContext', 'PWEventPcapInfo', 'DocumentationAutomation', 'GetCampaignIncidentsIdsAsOptions', 'JiraIssueQuery', 'CSActors', 'EPORetrieveCurrentDATVersion', 'JiraIssueAddLink', 'ShowCampaignUniqueSenders', 'SplunkEmailParser', 'ExchangeAssignRole', 'ADGetGroupMembers', 'GetCampaignIndicatorsByIncidentId', 'SearchIncidents', 'EntryWidgetPieAlertsXDR', 'IncidentToContext', 'ADGetUsersByEmail', 'PreprocessEmail', 'CPShowHosts', 'PWEventDetails', 'ExpanseEvidenceDynamicSection', 'CortexXDRAdditionalAlertInformationWidget', 'IsIPInSubnet', 'CrowdStrikeStreamingPreProcessing', 'CBFindHash', 'TaniumApprovePendingActions', 'ShowCampaignLastIncidentOccurred', 'DataURLReputation', 'PanoramaMove', 'IntegrationsCheck-Widget-IntegrationsCategory', 'ShowCampaignHighestSeverity', 'EntryWidgetNumberHostsXDR', 'ExposeList', 'ExposeUsers', 'IncidentsCheck-PlaybooksHealthNames', 'GoogleappsGmailSearch', 'ExtractDomain', 'TaniumAskQuestion', 'f99a85a6-c572-4c3a-8afd-5b4ac539000a', 'EPOCheckLatestDAT', 'CSIndicators', 'GetCampaignIncidentsInfo', 'SendEmailToCampaignRecipients', 'GoogleappsGetUserRoles', 'CPBlockIP', 'ExpanseEnrichAttribution', 'ConferSetSeverity', 'AdSearch', 'ExchangeSearchMailbox', 'MatchIPinCIDRIndicators', 'GetNumberOfUsersOnCall', 'XBUser', '82764532-0a4f-4b59-8cf9-fe1a00cabdae', 'PublishThreatIntelReport', 'PWFindEvents', 'IncidentsCheck-Widget-CommandsNames', 'ExtractDomainFromURL', 'PanoramaCommit', 'EPORepositoryComplianceCheck', 'EPOUpdateEndpoints', 'LCMDetectedIndicators', 'IncidentsCheck-Widget-CreationDate', 'PWEvents', 'IncidentsCheck-NumberofIncidentsNoOwner', 'ExpanseAggregateAttributionCI', 'SetPhishingCampaignDetails', 'QrFullSearch', 'InviteUser', 'ConferIncidentDetails', 'LCMPathFinderScanHost', 'GetUsersOnCall', 'VectraSummary', '3dd62013-4fed-43eb-8ae4-91b1b4250599', 'TriagePhishing', 'CollectCampaignRecipients', 'ExposeModules', '840aa9a7-04b2-4505-8238-8fe85f010dde', 'LCMSetHostComment', 'ADGetComputer', 'ReadPDFFile', 'ParseEmailFile', 'JiraIssueUploadFile', 'TimeToNextShift', 'NessusGetReport', 'CopyLinkedAnalystNotes', 'InstancesCheck-NumberofEnabledInstances', 'GetShiftsPerUser', 'TaniumFindRunningProcesses', 'GoogleappsGetUser', 'AwsGetInstanceInfo', 'HTMLDocsAutomation', 'EPORepoList', 'CPSetRule', 'ExpanseGenerateIssueMapWidgetScript', 'LCMHosts', 'ParseEmailHeader', 'JiraCreateIssue', 'IntegrationsCheck-Widget-IntegrationsErrorsInfo', 'SetSeverityByScore', 'QrSearches', 'AggregateIOCs', 'CPShowAccessRulebase', 'ClassifierNotifyAdmin', 'DBotPredictPhishingLabel', 'ExpanseParseRawIncident', 'CortexXDRIdentityInformationWidget', 'PanoramaDynamicAddressGroup', 'CreateChannelWrapper', 'ADListComputers', 'PanoramaConfig', 'XBTimeline', 'QrOffenses', 'DataDomainReputation', 'VectraHealth', 'GetAwayUsers', 'ManageOOOusers', 'GetOnCallHoursPerUser', 'ShowCampaignIncidentsOwners', 'GetContextValue', 'DataIPReputation', 'ExpanseAggregateAttributionDevice', 'LCMAcknowledgeHost', 'SNUpdateTicket', 'WhoisSummary', 'LCMDetectedEntities', 'XBNotable', 'FeedIntegrationErrorWidget', 'ADGetEmailForUser', 'IsIncidentPartOfCampaign', 'AwsCreateImage', 'CPCreateBackup', 'CheckFilesWildfirePy', 'GetRolesPerShift', 'IntegrationsCheck-Widget-NumberChecked', 'SplunkSearchJsonPy', 'ShowCampaignRecipients', 'QrGetSearchResults', 'NessusShowEditorTemplates', 'GoogleappsListUsers', 'IPExtract', 'ExpanseAggregateAttributionIP', 'VectraSensors', 'PWObservationPcapInfo', 'CYFileRep', 'RestartFailedTasks', 'DefaultIncidentClassifier', 'CheckIPs', 'MD5Extract', 'DBotPreparePhishingData', '94f72ed9-49c8-40e5-89bb-7c98f914d2cc', 'VectraGetDetetctionsById', 'AwsRunInstance', 'AwsStopInstance', 'CortexXDRCloudProviderWidget', 'ShowCampaignSimilarityRange', 'XDRSyncScript', 'JiraIssueAddComment', 'ADGetGroupComputers', 'GoogleappsRevokeUserRole', 'ADListUsersEx', 'RSSWidget', 'ADGetUserGroups', 'GetSendEmailInstances', 'SandboxDetonateFile', 'GetUsersOOO', 'MyToDoTasksWidget', 'CSCountDevicesForIOC', 'AwsCreateVolumeSnapshot', 'TaniumDeployAction', 'IncidentSet', 'ADIsUserMember', 'IncidentsCheck-Widget-IncidentsErrorsInfo', 'AssignAnalystToIncidentOOO', 'OutOfOfficeListCleanup', 'SendEmailReply', 'NessusScanStatus', 'PanoramaBlockIP', 'BinaryReputationPy', 'ADGetAllUsersEmail', 'ExpanseRefreshIssueAssets', 'PanoramaPcaps', 'ADListUsers', 'XBInfo', 'RunSqlQuery', 'IncidentsCheck-NumberofTotalEntriesErrors', 'ExpansePrintSuggestions', 'IncidentsCheck-PlaybooksFailingCommands', 'GetCampaignLowerSimilarityIncidentsIdsAsOptions', 'ShowNumberOfCampaignIncidents', 'ElasticSearchDisplay', 'CheckFiles', 'Elasticsearch', 'CSHuntByIOC', 'CloseInvestigation', 'InstancesCheck-FailedCategories', 'FindEmailCampaign', 'SlackMirror', 'WildfireReport', 'BlockIP', 'da330ce7-3a93-430c-8454-03b96cf5184e', '7b02fa0f-94ff-48c7-8350-b4e353702e73', 'QrGetSearch', 'ExchangeDeleteMail', 'GoogleAuthURL', 'DisplayEmailHtml', 'XBLockouts', 'LCMResolveHost', 'SetIncidentCustomFields', 'EPOUpdateRepository', 'IngestCSV', 'ADGetComputerGroups', 'CommonIntegration', 'SNListTickets', '10cb3486-48f3-4d93-88af-b6be84ffd432', 'GetFailedTasks', 'ADExpirePassword', 'LocateAttachment', 'GetCampaignDuration', 'ShowCampaignUniqueRecipients', 'EsmExample', 'InstancesCheck-NumberofFailedInstances', '9364c36f-b1d6-4233-88c2-75008b106c31', '514ec833-c02c-49a3-8ac6-d982198f5fa0', 'GoogleappsGmailGetMail', 'DBotTrainTextClassifier', 'CPDeleteRule', 'AwsStartInstance', 'IPInfoQuery', 'CBSearch', 'EntryWidgetNumberUsersXDR', 'NessusScanDetails', 'SplunkSearch', 'ProofpointDecodeURL', 'ADGetGroupUsers', 'NessusHostDetails', 'ADSetNewPassword', 'a6e348f4-1e40-4365-870c-52139c60779a', 'TaniumAskQuestionComplex', 'NetwitnessSAUpdateIncident', 'ExtractEmail', 'TaniumShowPendingActions', 'SplitCampaignContext', 'JiraGetIssue', 'VectraGetHostById', 'DBotPredictTextLabel', 'LCMIndicatorsForEntity', 'IsContextSet', 'PWObservations', 'JobCreator', 'GetLargestInputsAndOuputsInIncidents', 'dbbdc2e4-6105-4ee9-8e83-563a4b991a89', 'ExchangeSearch', 'SNOpenTicket', 'VectraDetections', 'IncidentsCheck-NumberofIncidentsWithErrors', 'IncidentsCheck-Widget-PlaybookNames', 'ADUserLogonInfo', 'VectraSettings', 'DBotPredictPhishingEvaluation', 'CheckWhitelist', 'PWSensors', 'EPODetermineRepository', 'ShowCampaignSenders', '2aa9f737-8c7c-42f5-815f-4d104bb3af06', 'XBTriggeredRules', 'ExtractIP', 'UnpublishThreatIntelReport', 'XDRDisconnectedEndpoints', '7b5c080e-f3b1-411a-83b0-e1f53c21bef8', 'DBotGroupXDRIncidents', 'PWObservationDetails', 'WildfireUpload', 'DataHashReputation', 'GetDuplicatesMl', 'ExpanseAggregateAttributionUser', 'XDRConnectedEndpoints', 'VectraClassifier', '80b5c44c-4eac-4e00-812f-6d409d57be31', 'URLExtract', 'NessusCreateScan', 'CPShowBackupStatus', 'IncidentsCheck-Widget-NumberofErrors', 'ExtractURL', 'IncidentsCheck-Widget-UnassignedFailingIncidents', 'AssignToNextShiftOOO', 'ADGetCommonGroups'}, 'classifier': {'ExpanseV2', '83d66f08-42b4-4ca6-8145-99bcf7c6b8e5', '173a8bc5-663b-4478-89a5-d2ce2ce8a31f', '0cc88f85-97b7-452e-839c-b58daf0bcf8d', 'MS Graph Mail Single User - Classifier - Email Communication', 'Wiz Classifier', '5d9a5ec5-33cb-4f82-8c5e-e8ae6f7831d8', 'Cortex XDR - IR', '6f81fb48-73d0-4f7f-8d3e-9c586ecec38a', '95573d05-345e-43b6-82f1-a5a8ad402e69', '32f26072-9a69-41a5-8db8-0d1226431078', 'faa1bfc8-09cd-44e0-81fe-73092e735916', '18a9fa04-f6e5-43cc-8427-a2ac0d94a8a2', 'crowdstrike-streaming-api', '5c83f473-c618-4c41-85d8-251eb1f90566', 'faa1bfc8-37cd-44e0-81fe-73092e381563'}, 'incidenttype': {'Integrations and Incidents Health Check', 'Cortex XDR Incident', 'Cortex XDR Disconnected endpoints', 'Expanse Appearance', 'Wiz Issue', 'Xpanse Issue - Generic', 'Cortex XDR Device Control Violations', 'Expanse Behavior', 'iDSAR', 'Cortex XDR - XCLOUD', 'Traps', 'Review Indicators Manually For Whitelisting', 'Review Indicators Manually', 'Expanse Issue', 'Shift handover', 'Email Communication', 'Cortex XDR Port Scan', 'Employee Offboarding', 'Phishing Campaign'}, 'incidentfield': {'incident_expanseassetowner', 'incident_expansemodified', 'incident_xdrnetworkartifacts', 'incident_selectaction', 'incident_expansecertificate', 'incident_integrationscategories', 'incident_expansebusinessunits', 'incident_totalgoodinstances', 'incident_wizresourceregion', 'incident_selectlowsimilarityincidents', 'incident_xdrhostcount', 'incident_xdrusers', 'incident_campaignmutualindicators', 'incident_xdrsimilarincidents', 'incident_googlemailstatus', 'incident_wizresourceid', 'incident_xdrmitretactics', 'incident_addcctoemail', 'incident_lastmirroredintime', 'incident_offboardingstage', 'incident_xdrdisconnectedendpoints', 'incident_expanseip', 'incident_playbooksfailedcommands', 'incident_xdrurl', 'incident_duoaccountstatus', 'incident_wizcloudaccountname', 'incident_totalfailedinstances', 'incident_devicegsuiteaccountstatus', 'incident_inventapiientities', 'incident_campaignemailsubject', 'incident_xdrhighseverityalertcount', 'incident_googleaccountstatus', 'incident_shiftopenincidents', 'incident_inventareportreason', 'incident_trapsid', 'incident_expanseseverity', 'incident_expanseinitialevidence', 'incident_expanserawjsonevent', 'incident_expanseexposuretype', 'incident_expanseassignee', 'incident_xdrusercount', 'incident_inventadsartransactions', 'incident_mailboxdelegation', 'incident_xdrassigneduserprettyname', 'incident_emailautoreply', 'incident_inventadsardatasubjectid', 'incident_tostartthemeeting', 'incident_playbookswithfailedtasks', 'incident_integrationstestgrid', 'incident_xdralertcount', 'incident_expanseprogressstatus', 'incident_xdrdevicecontrolviolations', 'incident_xdrnotes', 'incident_campaignemailbody', 'incident_wizissueduedate', 'incident_xdrfilesha256', 'incident_expansecreated', 'incident_xdralertname', 'incident_xdrlowseverityalertcount', 'incident_expanseissueid', 'incident_inventafullname', 'incident_wizissuenote', 'incident_tojointhemeeting', 'incident_xdrfilename', 'incident_expanseissuetype', 'incident_createddatefailedincidents', 'incident_companypropertystatus', 'incident_unassignedincidents', 'incident_xdrdetectiontime', 'incident_wizissueid', 'incident_inventacreditcardnumber', 'incident_xdrmitretechniques', 'incident_emailgeneratedcode', 'incident_expanseactivitystatus', 'incident_playbooktaskserrors', 'incident_actionsonlowsimilarityincidents', 'incident_wizdetails', 'incident_selectcampaignincidents', 'incident_campaignemailsenderinstance', 'incident_expanseprotocol', 'incident_wizresourcetype', 'incident_xdrassigneduseremail', 'incident_numberoffailedincidents', 'incident_expanseregion', 'incident_inventadsarinventaticket', 'incident_inventadriverlicense', 'incident_activedirectorypasswordstatus', 'incident_googledisplayname', 'incident_xdrmodificationtime', 'incident_inventapassportnumber', 'incident_outofftheoffice', 'incident_expanseprovider', 'incident_expanseasset', 'incident_xdrstatusv2', 'incident_inventadsardatasubjectemail', 'incident_xdralerts', 'incident_googlepasswordstatus', 'incident_xdrmediumseverityalertcount', 'incident_totalinstances', 'incident_shiftmanagerbriefing', 'incident_expansebusinessunit', 'incident_expanseshadowit', 'incident_offboardingdate', 'incident_activedirectorydisplayname', 'incident_expanseservice', 'incident_actionsoncampaignincidents', 'incident_expanseport', 'incident_inventavehiclenumber', 'incident_expansepriority', 'incident_xdrstatus', 'incident_incidentsinfo', 'incident_expansemlfeatures', 'incident_wizcloudaccount', 'incident_activedirectoryaccountstatus', 'incident_similarincident', 'incident_numberofentriesiderrors', 'incident_failedincidentscreateddate', 'incident_expansetags', 'incident_inventanationalid', 'incident_expansebehaviorrule', 'incident_campaignclosenotes', 'incident_xdrmanualseverity', 'incident_campaignemailto', 'incident_xdralertcategory', 'incident_inventadsarfiles', 'incident_playbooknameswithfailedtasks', 'incident_inventataxid', 'incident_inventadsardataassets', 'incident_expanseassetorganizationunit', 'incident_xdrfileartifacts', 'incident_expanselatestevidence', 'incident_inventadsardatabases', 'incident_integrationsfailedcategories', 'incident_expansecloudmanagementstatus', 'incident_googledrivestatus', 'incident_expansegeolocation', 'incident_oktaaccountstatus', 'incident_xdrdescription', 'incident_inventadsardatasubjectname', 'incident_globaldirectoryvisibility', 'incident_wizcloudplatform', 'incident_inventadsarpiientities', 'incident_inventabirthday', 'incident_xdrresolvecomment', 'incident_expansecategory', 'incident_xdrincidentid', 'incident_googleadminrolesstatus', 'incident_expansedomain'}, 'indicatorfield': {'indicator_expanselastobserved', 'indicator_expansedomain', 'indicator_expansedateadded', 'indicator_xdrstatus', 'indicator_expanseproperties', 'indicator_feedmandiantversion', 'indicator_expansednsresolutionstatus', 'indicator_expansetenantname', 'indicator_expansecertificateadvertisementstatus', 'indicator_expanseassettype', 'indicator_expansefirstobserved', 'indicator_expansesourcedomain', 'indicator_expansebusinessunits', 'indicator_expansetags', 'indicator_feedmandiantdetections', 'indicator_expanseservicestatus', 'indicator_feedmandiantreportid', 'indicator_expanseprovidername', 'indicator_expansetype'}, 'mapper': {'crowdstrike-streaming-api-mapper', 'User Profile - SCIM (Incoming)', '4f31271a-c22a-4615-862d-2e315778676e', 'e92f424d-51f4-4d7c-8e35-502f2a4dac02', 'ExpanseV2-mapper', 'Cortex XDR - IR-out-mapper', 'fd0fde44-a619-4273-8c70-569f6620d759', 'MS Graph Mail Single User - Incoming Mapper - Email Communication', 'Wiz Mapper Webhook', 'Wiz Mapper', 'Cortex XDR - IR-mapper', 'User Profile - SCIM (Outgoing)'}}
    if excluded_items_by_pack:
        remove_dependencies_from_id_set(id_set, excluded_items_by_pack, excluded_items_by_type)
        id_set_creator.save_id_set()


# ====================== merge-id-sets ====================== #
@main.command(hidden=True)
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i1', '--id-set1',
    help='First id_set.json file path',
    required=True
)
@click.option(
    '-i2', '--id-set2',
    help='Second id_set.json file path',
    required=True
)
@click.option(
    '-o', '--output',
    help='File path of the united id_set',
    required=True
)
@click.option(
    '-fd',
    '--fail-duplicates',
    help="Fails the process if any duplicates are found.",
    is_flag=True
)
def merge_id_sets(**kwargs):
    """Merge two id_sets"""
    from demisto_sdk.commands.common.update_id_set import \
        merge_id_sets_from_files
    check_configuration_file('merge-id-sets', kwargs)
    first = kwargs['id_set1']
    second = kwargs['id_set2']
    output = kwargs['output']
    fail_duplicates = kwargs['fail_duplicates']

    _, duplicates = merge_id_sets_from_files(
        first_id_set_path=first,
        second_id_set_path=second,
        output_id_set_path=output
    )
    if duplicates:
        print_error(f'Failed to merge ID sets: {first} with {second}, '
                    f'there are entities with ID: {duplicates} that exist in both ID sets')
        if fail_duplicates:
            sys.exit(1)


# ====================== update-release-notes =================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input", help="The relative path of the content pack. For example Packs/Pack_Name"
)
@click.option(
    '-u', '--update-type', help="The type of update being done. [major, minor, revision, maintenance, documentation]",
    type=click.Choice(['major', 'minor', 'revision', 'maintenance', 'documentation'])
)
@click.option(
    '-v', '--version', help="Bump to a specific version.", type=VersionParamType()
)
@click.option(
    '-g', '--use-git',
    help="Use git to identify the relevant changed files, will be used by default if '-i' is not set",
    is_flag=True
)
@click.option(
    '-f', '--force', help="Force update release notes for a pack (even if not required).", is_flag=True
)
@click.option(
    '--text', help="Text to add to all of the release notes files.",
)
@click.option(
    '--prev-ver', help='Previous branch or SHA1 commit to run checks against.'
)
@click.option(
    "--pre_release", help="Indicates that this change should be designated a pre-release version.",
    is_flag=True)
@click.option(
    "-idp", "--id-set-path", help="The path of the id-set.json used for APIModule updates.",
    type=click.Path(resolve_path=True))
@click.option(
    '-bc', '--breaking-changes', help='If new version contains breaking changes.',
    is_flag=True)
def update_release_notes(**kwargs):
    """Auto-increment pack version and generate release notes template."""
    from demisto_sdk.commands.update_release_notes.update_rn_manager import \
        UpdateReleaseNotesManager
    check_configuration_file('update-release-notes', kwargs)
    if kwargs.get('force') and not kwargs.get('input'):
        print_error('Please add a specific pack in order to force a release notes update.')
        sys.exit(0)

    if not kwargs.get('use_git') and not kwargs.get('input'):
        click.confirm('No specific pack was given, do you want to update all changed packs?', abort=True)

    try:
        rn_mng = UpdateReleaseNotesManager(user_input=kwargs.get('input'), update_type=kwargs.get('update_type'),
                                           pre_release=kwargs.get('pre_release', False), is_all=kwargs.get('use_git'),
                                           text=kwargs.get('text'), specific_version=kwargs.get('version'),
                                           id_set_path=kwargs.get('id_set_path'), prev_ver=kwargs.get('prev_ver'),
                                           is_force=kwargs.get('force', False),
                                           is_bc=kwargs.get('breaking_changes', False))
        rn_mng.manage_rn_update()
        sys.exit(0)
    except Exception as e:
        print_error(f'An error occurred while updating the release notes: {str(e)}')
        sys.exit(1)


# ====================== find-dependencies ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input", help="Pack path to find dependencies. For example: Pack/HelloWorld. When using the"
                          " --get-dependent-on flag, this argument can be used multiple times.", required=False,
    type=click.Path(exists=True, dir_okay=True), multiple=True)
@click.option(
    "-idp", "--id-set-path", help="Path to id set json file.", required=False, default='')
@click.option(
    "--no-update", help="Use to find the pack dependencies without updating the pack metadata.", required=False,
    is_flag=True)
@click.option('-v', "--verbose", help="Whether to print the log to the console.", required=False,
              is_flag=True)
@click.option("--use-pack-metadata", help="Whether to update the dependencies from the pack metadata.", required=False,
              is_flag=True)
@click.option("--all-packs-dependencies", help="Return a json file with ALL content packs dependencies. "
                                               "The json file will be saved under the path given in the "
                                               "'--output-path' argument", required=False, is_flag=True)
@click.option("-o", "--output-path", help="The destination path for the packs dependencies json file. This argument is "
              "only relevant for when using the '--all-packs-dependecies' flag.", required=False)
@click.option("--get-dependent-on", help="Get only the packs dependent ON the given pack. Note: this flag can not be"
                                         " used for the packs ApiModules and Base", required=False,
              is_flag=True)
def find_dependencies(**kwargs):
    """Find pack dependencies and update pack metadata."""
    from demisto_sdk.commands.find_dependencies.find_dependencies import \
        PackDependencies
    check_configuration_file('find-dependencies', kwargs)
    update_pack_metadata = not kwargs.get('no_update')
    input_paths = kwargs.get('input')  # since it can be multiple, received as a tuple
    verbose = kwargs.get('verbose', False)
    id_set_path = kwargs.get('id_set_path', '')
    use_pack_metadata = kwargs.get('use_pack_metadata', False)
    all_packs_dependencies = kwargs.get('all_packs_dependencies', False)
    get_dependent_on = kwargs.get('get_dependent_on', False)
    output_path = kwargs.get('output_path', ALL_PACKS_DEPENDENCIES_DEFAULT_PATH)

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
        )

    except ValueError as exp:
        print_error(str(exp))


# ====================== postman-codegen ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input',
    help='The Postman collection 2.1 JSON file',
    required=True, type=click.File())
@click.option(
    '-o', '--output',
    help='The output directory to save the config file or the integration',
    type=click.Path(dir_okay=True, exists=True),
    default=Path('.'),
    show_default=True
)
@click.option(
    '-n', '--name',
    help='The output integration name')
@click.option(
    '-op', '--output-prefix',
    help='The global integration output prefix. By default it is the product name.'
)
@click.option(
    '-cp', '--command-prefix',
    help='The prefix for each command in the integration. By default is the product name in lower case'
)
@click.option(
    '--config-out',
    help='Used for advanced integration customisation. Generates a config json file instead of integration.',
    is_flag=True
)
@click.option(
    '--verbose', help='Print debug level logs', is_flag=True)
@click.option(
    '-p', '--package',
    help='Generated integration will be split to package format instead of a yml file.',
    is_flag=True
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
        package: bool
):
    """Generates a Cortex XSOAR integration given a Postman collection 2.1 JSON file."""
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.postman_codegen.postman_codegen import \
        postman_to_autogen_configuration
    from demisto_sdk.commands.split.ymlsplitter import YmlSplitter

    if verbose:
        logger = logging_setup(verbose=3)
    else:
        logger = logging.getLogger('demisto-sdk')

    postman_config = postman_to_autogen_configuration(
        collection=json.load(input),
        name=name,
        command_prefix=command_prefix,
        context_path_prefix=output_prefix
    )

    if config_out:
        path = Path(output) / f'config-{postman_config.name}.json'
        path.write_text(json.dumps(postman_config.to_dict(), indent=4))
        logger.info(f'Config file generated at:\n{str(path.absolute())}')
    else:
        # generate integration yml
        yml_path = postman_config.generate_integration_package(output, is_unified=True)
        if package:
            yml_splitter = YmlSplitter(configuration=config.configuration, file_type=FileType.INTEGRATION.value,
                                       input=str(yml_path), output=str(output))
            yml_splitter.extract_to_package_format()


# ====================== generate-integration ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input',
    help='config json file produced by commands like postman-codegen and openapi-codegen',
    required=True,
    type=click.File()
)
@click.option(
    '-o', '--output',
    help='The output directory to save the integration package',
    type=click.Path(dir_okay=True, exists=True),
    default=Path('.')
)
@click.option(
    '--verbose',
    help='Print debug level logs',
    is_flag=True
)
def generate_integration(input: IO, output: Path, verbose: bool):
    """Generates a Cortex XSOAR integration from a config json file,
    which is generated by commands like postman-codegen
    """
    from demisto_sdk.commands.common.logger import logging_setup
    from demisto_sdk.commands.generate_integration.code_generator import \
        IntegrationGeneratorConfig
    if verbose:
        logging_setup(verbose=3)

    config_dict = json.load(input)
    config = IntegrationGeneratorConfig(**config_dict)

    config.generate_integration_package(output, True)


# ====================== openapi-codegen ====================== #
@main.command(short_help='''Generates a Cortex XSOAR integration given an OpenAPI specification file.''')
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input_file', help='The swagger file to load in JSON format', required=True)
@click.option(
    '-cf', '--config_file', help='The integration configuration file. It is created in the first run of the command',
    required=False)
@click.option(
    '-n', '--base_name', help='The base filename to use for the generated files', required=False)
@click.option(
    '-o', '--output_dir', help='Directory to store the output in (default is current working directory)',
    required=False)
@click.option(
    '-pr', '--command_prefix', help='Add a prefix to each command in the code', required=False)
@click.option(
    '-c', '--context_path', help='Context output path', required=False)
@click.option(
    '-u', '--unique_keys', help='Comma separated unique keys to use in context paths (case sensitive)', required=False)
@click.option(
    '-r', '--root_objects', help='Comma separated JSON root objects to use in command outputs (case sensitive)',
    required=False)
@click.option(
    '-v', '--verbose', is_flag=True, help='Be verbose with the log output')
@click.option(
    '-f', '--fix_code', is_flag=True, help='Fix the python code using autopep8')
@click.option(
    '-a', '--use_default', is_flag=True, help='Use the automatically generated integration configuration'
                                              ' (Skip the second run).')
def openapi_codegen(**kwargs):
    """Generates a Cortex XSOAR integration given an OpenAPI specification file.
    In the first run of the command, an integration configuration file is created, which can be modified.
    Then, the command is run a second time with the integration configuration to generate the actual integration files.
    """
    from demisto_sdk.commands.openapi_codegen.openapi_codegen import \
        OpenAPIIntegration
    check_configuration_file('openapi-codegen', kwargs)
    if not kwargs.get('output_dir'):
        output_dir = os.getcwd()
    else:
        output_dir = kwargs['output_dir']

    # Check the directory exists and if not, try to create it
    if not os.path.exists(output_dir):
        try:
            os.mkdir(output_dir)
        except Exception as err:
            print_error(f'Error creating directory {output_dir} - {err}')
            sys.exit(1)
    if not os.path.isdir(output_dir):
        print_error(f'The directory provided "{output_dir}" is not a directory')
        sys.exit(1)

    input_file = kwargs['input_file']
    base_name = kwargs.get('base_name')
    if base_name is None:
        base_name = 'GeneratedIntegration'

    command_prefix = kwargs.get('command_prefix')
    if command_prefix is None:
        command_prefix = '-'.join(base_name.split(' ')).lower()

    context_path = kwargs.get('context_path')
    if context_path is None:
        context_path = base_name.replace(' ', '')

    unique_keys = kwargs.get('unique_keys', '')
    if unique_keys is None:
        unique_keys = ''

    root_objects = kwargs.get('root_objects', '')
    if root_objects is None:
        root_objects = ''

    verbose = kwargs.get('verbose', False)
    fix_code = kwargs.get('fix_code', False)

    configuration = None
    if kwargs.get('config_file'):
        try:
            with open(kwargs['config_file'], 'r') as config_file:
                configuration = json.load(config_file)
        except Exception as e:
            print_error(f'Failed to load configuration file: {e}')

    click.echo('Processing swagger file...')
    integration = OpenAPIIntegration(input_file, base_name, command_prefix, context_path,
                                     unique_keys=unique_keys, root_objects=root_objects,
                                     verbose=verbose, fix_code=fix_code, configuration=configuration)

    integration.load_file()
    if not kwargs.get('config_file'):
        integration.save_config(integration.configuration, output_dir)
        print_success(f'Created configuration file in {output_dir}')
        if not kwargs.get('use_default', False):
            config_path = os.path.join(output_dir, f'{base_name}_config.json')
            command_to_run = f'demisto-sdk openapi-codegen -i "{input_file}" -cf "{config_path}" -n "{base_name}" ' \
                             f'-o "{output_dir}" -pr "{command_prefix}" -c "{context_path}"'
            if unique_keys:
                command_to_run = command_to_run + f' -u "{unique_keys}"'
            if root_objects:
                command_to_run = command_to_run + f' -r "{root_objects}"'
            if verbose:
                command_to_run = command_to_run + ' -v'
            if fix_code:
                command_to_run = command_to_run + ' -f'

            click.echo(f'Run the command again with the created configuration file(after a review): {command_to_run}')
            sys.exit(0)

    if integration.save_package(output_dir):
        print_success(f'Successfully finished generating integration code and saved it in {output_dir}')
    else:
        print_error(f'There was an error creating the package in {output_dir}')
        sys.exit(1)


# ====================== test-content command ====================== #
@main.command(
    short_help='''Created incidents for selected test-playbooks and gives a report about the results''',
    hidden=True
)
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-k', '--api-key', help='The Demisto API key for the server', required=True)
@click.option(
    '-s', '--server', help='The server URL to connect to')
@click.option(
    '-c', '--conf', help='Path to content conf.json file', required=True)
@click.option(
    '-e', '--secret', help='Path to content-test-conf conf.json file')
@click.option(
    '-n', '--nightly', type=bool, help='Run nightly tests')
@click.option(
    '-t', '--slack', help='The token for slack', required=True)
@click.option(
    '-a', '--circleci', help='The token for circleci', required=True)
@click.option(
    '-b', '--build-number', help='The build number', required=True)
@click.option(
    '-g', '--branch-name', help='The current content branch name', required=True)
@click.option(
    '-i', '--is-ami', type=bool, help='is AMI build or not', default=False)
@click.option(
    '-m',
    '--mem-check',
    type=bool,
    help='Should trigger memory checks or not. The slack channel to check the data is: '
         'dmst_content_nightly_memory_data',
    default=False)
@click.option(
    '-d',
    '--server-version',
    help='Which server version to run the tests on(Valid only when using AMI)',
    default="NonAMI")
def test_content(**kwargs):
    """Configure instances for the integration needed to run tests_to_run tests.
    Run test module on each integration.
    create an investigation for each test.
    run test playbook on the created investigation using mock if possible.
    Collect the result and give a report.
    """
    from demisto_sdk.commands.test_content.execute_test_content import \
        execute_test_content
    check_configuration_file('test-content', kwargs)
    execute_test_content(**kwargs)


# ====================== doc-review ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input', type=str, help='The path to the file to check')
@click.option(
    '--no-camel-case', is_flag=True, help='Whether to check CamelCase words', default=False)
@click.option(
    '--known-words', type=str, help="The path to a file containing additional known words"
)
@click.option(
    '--always-true', is_flag=True, help="Whether to fail the command if misspelled words are found"
)
@click.option(
    '--expand-dictionary', is_flag=True, help="Whether to expand the base dictionary to include more words - "
                                              "will download 'brown' corpus from nltk package"
)
@click.option(
    '--templates', is_flag=True, help="Whether to print release notes templates"
)
@click.option(
    '-g', '--use-git', is_flag=True, help="Use git to identify the relevant changed files, "
                                          "will be used by default if '-i' and '--templates' are not set"
)
@click.option(
    '--prev-ver', type=str, help="The branch against which changes will be detected "
                                 "if '-g' flag is set. Default is 'demisto/master'"
)
@click.option(
    '-rn', '--release-notes', is_flag=True, help="Will run only on release notes files"
)
def doc_review(**kwargs):
    """Check the spelling in .md and .yml files as well as review release notes"""
    from demisto_sdk.commands.doc_reviewer.doc_reviewer import DocReviewer
    doc_reviewer = DocReviewer(
        file_path=kwargs.get('input'),
        known_words_file_path=kwargs.get('known_words'),
        no_camel_case=kwargs.get('no_camel_case'),
        no_failure=kwargs.get('always_true'),
        expand_dictionary=kwargs.get('expand_dictionary'),
        templates=kwargs.get('templates'),
        use_git=kwargs.get('use_git'),
        prev_ver=kwargs.get('prev_ver'),
        release_notes_only=kwargs.get('release_notes'),
    )
    result = doc_reviewer.run_doc_review()
    if result:
        sys.exit(0)

    sys.exit(1)


# ====================== integration-diff ====================== #
@main.command(name="integration-diff",
              help='''Given two versions of an integration, Check that everything in the old integration is covered in
              the new integration''')
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-n', '--new', type=str, help='The path to the new version of the integration', required=True)
@click.option(
    '-o', '--old', type=str, help='The path to the old version of the integration', required=True)
@click.option(
    '--docs-format', is_flag=True,
    help='Whether output should be in the format for the version differences section in README.')
def integration_diff(**kwargs):
    """
    Checks for differences between two versions of an integration, and verified that the new version covered the old version.
    """
    from demisto_sdk.commands.integration_diff.integration_diff_detector import \
        IntegrationDiffDetector
    integration_diff_detector = IntegrationDiffDetector(
        new=kwargs.get('new', ''),
        old=kwargs.get('old', ''),
        docs_format=kwargs.get('docs_format', False)
    )
    result = integration_diff_detector.check_different()

    if result:
        sys.exit(0)

    sys.exit(1)


# ====================== convert ====================== #
@main.command()
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input', type=click.Path(exists=True), required=True,
    help='The path of the content pack/directory/file to convert.'
)
@click.option(
    '-v', '--version', required=True, help="Version the input to be compatible with."
)
@pass_config
def convert(config, **kwargs):
    """
    Convert the content of the pack/directory in the given input to be compatible with the version given by
    version command.
    """
    from demisto_sdk.commands.convert.convert_manager import ConvertManager
    check_configuration_file('convert', kwargs)
    sys.path.append(config.configuration.env_dir)

    input_path = kwargs['input']
    server_version = kwargs['version']
    convert_manager = ConvertManager(input_path, server_version)
    result = convert_manager.convert()

    if result:
        sys.exit(1)

    sys.exit(0)


@main.command(
    name='error-code',
    help='Quickly find relevant information regarding an error code.',
)
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input', required=True,
    help='The error code to search for.',
)
@pass_config
def error_code(config, **kwargs):
    from demisto_sdk.commands.error_code_info.error_code_info import \
        generate_error_code_information
    check_configuration_file('error-code-info', kwargs)
    sys.path.append(config.configuration.env_dir)

    result = generate_error_code_information(kwargs.get('input'))

    sys.exit(result)


@main.resultcallback()
def exit_from_program(result=0, **kwargs):
    sys.exit(result)


if __name__ == '__main__':
    main()
