# Site packages
import json
import os
import sys
from pathlib import Path

from pkg_resources import get_distribution

# Third party packages
import click
import git
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.configuration import Configuration
# Common tools
from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK, SKIP_RELEASE_NOTES_FOR_TYPES, FileType)
from demisto_sdk.commands.common.tools import (filter_files_by_type,
                                               filter_files_on_pack, find_type,
                                               get_last_remote_release_version,
                                               get_pack_name, print_error,
                                               print_warning)
from demisto_sdk.commands.common.update_id_set import merge_id_sets_from_files
from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
    ArtifactsManager, create_content_artifacts)
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from demisto_sdk.commands.download.downloader import Downloader
from demisto_sdk.commands.find_dependencies.find_dependencies import \
    PackDependencies
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.generate_docs.generate_integration_doc import \
    generate_integration_doc
from demisto_sdk.commands.generate_docs.generate_playbook_doc import \
    generate_playbook_doc
from demisto_sdk.commands.generate_docs.generate_script_doc import \
    generate_script_doc
from demisto_sdk.commands.generate_test_playbook.test_playbook_generator import \
    PlaybookTestsGenerator
from demisto_sdk.commands.init.initiator import Initiator
from demisto_sdk.commands.json_to_outputs.json_to_outputs import \
    json_to_outputs
from demisto_sdk.commands.lint.lint_manager import LintManager
from demisto_sdk.commands.openapi_codegen.openapi_codegen import \
    OpenAPIIntegration
# Import demisto-sdk commands
from demisto_sdk.commands.run_cmd.runner import Runner
from demisto_sdk.commands.run_playbook.playbook_runner import PlaybookRunner
from demisto_sdk.commands.secrets.secrets import SecretsValidator
from demisto_sdk.commands.split_yml.extractor import Extractor
from demisto_sdk.commands.test_content.execute_test_content import \
    execute_test_content
from demisto_sdk.commands.unify.unifier import Unifier
from demisto_sdk.commands.update_release_notes.update_rn import (
    UpdateRN, update_api_modules_dependents_rn)
from demisto_sdk.commands.upload.uploader import Uploader
from demisto_sdk.commands.validate.validate_manager import ValidateManager


class DemistoSDK:
    """
    The core class for the SDK.
    """

    def __init__(self):
        self.configuration = None


pass_config = click.make_pass_decorator(DemistoSDK, ensure=True)


@click.group(invoke_without_command=True, no_args_is_help=True, context_settings=dict(max_content_width=100), )
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-v', '--version', help='Get the demisto-sdk version.',
    is_flag=True, default=False, show_default=True
)
@pass_config
def main(config, version):
    config.configuration = Configuration()
    cur_version = get_distribution('demisto-sdk').version
    last_release = get_last_remote_release_version()
    if last_release and cur_version != last_release:
        print_warning(f'You are using demisto-sdk {cur_version}, however version {last_release} is available.\n'
                      f'You should consider upgrading via "pip3 install --upgrade demisto-sdk" command.')
    if version:
        version = get_distribution('demisto-sdk').version
        print(f'demisto-sdk {version}')


# ====================== split-yml ====================== #
@main.command(name="split-yml",
              short_help="Split the code, image and description files from a Demisto integration or script yaml file "
                         " to multiple files(To a package format - "
                         "https://demisto.pan.dev/docs/package-dir).")
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input', help='The yml file to extract from', required=True
)
@click.option(
    '-o', '--output', required=True,
    help="The output dir to write the extracted code/description/image to."
)
@click.option(
    '--no-demisto-mock',
    help="Don't add an import for demisto mock.",
    is_flag=True,
    show_default=True
)
@click.option(
    '--no-common-server',
    help="Don't add an import for CommonServerPython.",
    is_flag=True,
    show_default=True
)
@click.option(
    '--no-auto-create-dir',
    help="Don't auto create the directory if the target directory ends with *Integrations/*Scripts.",
    is_flag=True,
    show_default=True
)
@pass_config
def extract(config, **kwargs):
    file_type: FileType = find_type(kwargs.get('input', ''), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT]:
        print_error('File is not an Integration or Script.')
        return 1
    extractor = Extractor(configuration=config.configuration, file_type=file_type.value, **kwargs)
    return extractor.extract_to_package_format()


# ====================== extract-code ====================== #
@main.command(
    name="extract-code",
    hidden=True,
    short_help="Extract code from a Demisto integration or script yaml file.")
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
    file_type: FileType = find_type(kwargs.get('input', ''), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT]:
        print_error('File is not an Integration or Script.')
        return 1
    extractor = Extractor(configuration=config.configuration, file_type=file_type.value, **kwargs)
    return extractor.extract_code(kwargs['outfile'])


# ====================== unify ====================== #
@main.command(
    name="unify",
    short_help='Unify code, image, description and yml files to a single Demisto yml file. Note that '
               'this should be used on a single integration/script and not a pack '
               'not multiple scripts/integrations')
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
    # Input is of type Path.
    kwargs['input'] = str(kwargs['input'])
    unifier = Unifier(**kwargs)
    unifier.merge_script_package_to_yml()
    return 0


# ====================== validate ====================== #
@main.command(
    short_help='Validate your content files. If no additional flags are given, will validated only '
               'committed files'
)
@click.help_option(
    '-h', '--help'
)
@click.option(
    '--no-conf-json', is_flag=True,
    default=False, show_default=True, help='Skip conf.json validation')
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
    help='Validate changes using git - this will check current branch\'s changes against origin/master. '
         'If the --post-commit flag is supplied: validation will run only on the current branch\'s changed files '
         'that have been committed. '
         'If the --post-commit flag is not supplied: validation will run on all changed files in the current branch, '
         'both committed and not committed. ')
@click.option(
    '--post-commit',
    is_flag=True,
    help='Whether the validation should run only on the current branch\'s committed changed files. '
         'This applies only when the -g flag is supplied.'
)
@click.option(
    '--staged',
    is_flag=True,
    help='Whether the validation should ignore unstaged files.'
         'This applies only when the -g flag is supplied.'
)
@click.option(
    '-a', '--validate-all', is_flag=True, show_default=True, default=False,
    help='Whether to run all validation on all files or not'
)
@click.option(
    '-i', '--input', type=click.Path(exists=True), help='The path of the content pack/file to validate specifically.'
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
@pass_config
def validate(config, **kwargs):
    sys.path.append(config.configuration.env_dir)

    file_path = kwargs['input']

    if kwargs['post_commit'] and kwargs['staged']:
        print_error('Could not supply the staged flag with the post-commit flag')
        sys.exit(1)
    try:
        is_external_repo = tools.is_external_repository()
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
            create_id_set=kwargs.get('create-id-set')
        )
        return validator.run_validation()
    except (git.InvalidGitRepositoryError, git.NoSuchPathError, FileNotFoundError) as e:
        print_error(e)
        print_error("\nYou may not be running `demisto-sdk validate` command in the content directory.\n"
                    "Please run the command from content directory")
        sys.exit(1)


# ====================== create-content-artifacts ====================== #
@main.command(
    name="create-content-artifacts",
    hidden=True,
    short_help='Generating the following artifacts:'
               '1. content_new - Contains all content objects of type json,yaml (from_version < 6.0.0)'
               '2. content_packs - Contains all packs from Packs - Ignoring internal files (to_version >= 6.0.0).'
               '3. content_test - Contains all test scripts/playbooks (from_version < 6.0.0)'
               '4. content_all - Contains all from content_new and content_test.')
@click.help_option('-h', '--help')
@click.option('-a', '--artifacts_path', help='Destination directory to create the artifacts.',
              type=click.Path(file_okay=False, resolve_path=True), required=True)
@click.option('--zip/--no-zip', help='Zip content artifacts folders', default=True)
@click.option('--packs', help='Create only content_packs artifacts.', is_flag=True)
@click.option('-v', '--content_version', help='The content version in CommonServerPython.', default='0.0.0')
@click.option('-s', '--suffix', help='Suffix to add all yaml/json/yml files in the created artifacts.')
@click.option('--cpus',
              help='Number of cpus/vcpus availble - only required when os not reflect number of cpus (CircleCI'
                   'allways show 32, but medium has 3.', hidden=True, default=os.cpu_count())
def create_arifacts(**kwargs) -> int:
    artifacts_conf = ArtifactsManager(**kwargs)
    return create_content_artifacts(artifacts_conf)


# ====================== secrets ====================== #
@main.command(name="secrets",
              short_help="Run Secrets validator to catch sensitive data before exposing your code to public repository."
                         " Attach path to whitelist to allow manual whitelists. Default file path to secrets is "
                         "'./Tests/secrets_white_list.json' ")
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input', help='Specify file of to check secret on.', required=False
)
@click.option(
    '--post-commit', is_flag=True, show_default=True,
    help='Whether the secretes is done after you committed your files, '
         'this will help the command to determine which files it should check in its '
         'run. Before you commit the files it should not be used. Mostly for build '
         'validations.')
@click.option(
    '-ie', '--ignore-entropy', is_flag=True,
    help='Ignore entropy algorithm that finds secret strings (passwords/api keys)'
)
@click.option(
    '-wl', '--whitelist', default='./Tests/secrets_white_list.json', show_default=True,
    help='Full path to whitelist file, file name should be "secrets_white_list.json"')
@click.option(
    '--prev-ver', help='The branch against which to run secrets validation')
@pass_config
def secrets(config, **kwargs):
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
@main.command(name="lint",
              short_help="Lint command will perform:\n 1. Package in host checks - flake8, bandit, mypy, vulture.\n 2. "
                         "Package in docker image checks -  pylint, pytest, powershell - test, powershell - analyze.\n "
                         "Meant to be used with integrations/scripts that use the folder (package) structure. "
                         "Will lookup up what docker image to use and will setup the dev dependencies and "
                         "file in the target folder. If no additional flags specifying the packs are given,"
                         " will lint only changed files")
@click.help_option('-h', '--help')
@click.option("-i", "--input", help="Specify directory of integration/script", type=click.Path(exists=True,
                                                                                               resolve_path=True))
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
@click.option("--prev-ver", default='master', help="Previous branch or SHA1 commit to run checks against")
@click.option("--test-xml", help="Path to store pytest xml results", type=click.Path(exists=True, resolve_path=True))
@click.option("--failure-report", help="Path to store failed packs report",
              type=click.Path(exists=True, resolve_path=True))
@click.option("-lp", "--log-path", help="Path to store all levels of logs",
              type=click.Path(exists=True, resolve_path=True))
def lint(input: str, git: bool, all_packs: bool, verbose: int, quiet: bool, parallel: int, no_flake8: bool,
         no_bandit: bool, no_mypy: bool, no_vulture: bool, no_xsoar_linter: bool, no_pylint: bool, no_test: bool,
         no_pwsh_analyze: bool,
         no_pwsh_test: bool, keep_container: bool, prev_ver: str, test_xml: str, failure_report: str, log_path: str):
    """Lint command will perform:\n
        1. Package in host checks - flake8, bandit, mypy, vulture.\n
        2. Package in docker image checks -  pylint, pytest, powershell - test, powershell - analyze.\n
    Meant to be used with integrations/scripts that use the folder (package) structure. Will lookup up what
    docker image to use and will setup the dev dependencies and file in the target folder."""
    lint_manager = LintManager(input=input,
                               git=git,
                               all_packs=all_packs,
                               verbose=verbose,
                               quiet=quiet,
                               log_path=log_path,
                               prev_ver=prev_ver)
    return lint_manager.run_dev_packages(parallel=parallel,
                                         no_flake8=no_flake8,
                                         no_bandit=no_bandit,
                                         no_mypy=no_mypy,
                                         no_vulture=no_vulture,
                                         no_xsoar_linter=no_xsoar_linter,
                                         no_pylint=no_pylint,
                                         no_test=no_test,
                                         no_pwsh_analyze=no_pwsh_analyze,
                                         no_pwsh_test=no_pwsh_test,
                                         keep_container=keep_container,
                                         test_xml=test_xml,
                                         failure_report=failure_report)


# ====================== format ====================== #
@main.command(name="format",
              short_help="Run formatter on a given script/playbook/integration/incidentfield/indicatorfield/"
                         "incidenttype/indicatortype/layout/dashboard/classifier/mapper/widget/report file. ")
@click.help_option(
    '-h', '--help')
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
def format_yml(**kwargs):
    return format_manager(**kwargs)


# ====================== upload ====================== #
@main.command(name="upload",
              short_help="Upload integration to Demisto instance. DEMISTO_BASE_URL environment variable should contain"
                         " the Demisto server base URL. DEMISTO_API_KEY environment variable should contain a valid "
                         "Demisto API Key."
                         " * Note: Uploading classifiers to Cortex XSOAR is available from version 6.0.0 and up.*")
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input", help="The path of file or a directory to upload. The following are supported:\n"
                          "- Pack\n"
                          "- A content entity directory that is inside a pack. For example: an Integrations "
                          "directory or a Layouts directory.\n"
                          "- Valid file that can be imported to Cortex XSOAR manually. For example a playbook: "
                          "helloWorld.yml", required=True)
@click.option(
    "--insecure", help="Skip certificate validation", is_flag=True)
@click.option(
    "-v", "--verbose", help="Verbose output", is_flag=True)
def upload(**kwargs):
    uploader = Uploader(**kwargs)
    return uploader.upload()


# ====================== download ====================== #


@main.command(name="download",
              short_help="Download custom content from Demisto instance. DEMISTO_BASE_URL environment variable should"
                         " contain the Demisto server base URL. DEMISTO_API_KEY environment variable should contain"
                         " a valid Demisto API Key.")
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
    downloader: Downloader = Downloader(**kwargs)
    return downloader.download()


# ====================== run ====================== #
@main.command(name="run",
              short_help="Run integration command on remote Demisto instance in the playground. DEMISTO_BASE_URL "
                         "environment variable should contain the Demisto base URL. DEMISTO_API_KEY environment "
                         "variable should contain a valid Demisto API Key.")
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
    runner = Runner(**kwargs)
    return runner.run()


# ====================== run-playbook ====================== #
@main.command(name="run-playbook",
              short_help="Run a playbook in Demisto. "
                         "DEMISTO_API_KEY environment variable should contain a valid Demisto API Key. "
                         "Example: DEMISTO_API_KEY=<API KEY> demisto-sdk run-playbook -p 'p_name' -u "
                         "'https://demisto.local'.")
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
    "--insecure", help="Skip certificate validation", is_flag=True)
def run_playbook(**kwargs):
    playbook_runner = PlaybookRunner(**kwargs)
    return playbook_runner.run_playbook()


# ====================== json-to-outputs ====================== #
@main.command(name="json-to-outputs",
              short_help='''Demisto integrations/scripts have a YAML file that defines them.
Creating the YAML file is a tedious and error-prone task of manually copying outputs from the API result to the
file/UI/PyCharm. This script auto generates the YAML for a command from the JSON result of the relevant API call.''')
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-c", "--command", help="Command name (e.g. xdr-get-incidents)", required=True)
@click.option(
    "-i", "--input",
    help="Valid JSON file path. If not specified, the script will wait for user input in the terminal. "
         "The response can be obtained by running the command with `raw-response=true` argument.",
    required=False)
@click.option(
    "-p", "--prefix", help="Output prefix like Jira.Ticket, VirusTotal.IP, the base path for the outputs that the "
                           "script generates", required=True)
@click.option(
    "-o", "--output", help="Output file path, if not specified then will print to stdout", required=False)
@click.option(
    "-v", "--verbose", is_flag=True, help="Verbose output - mainly for debugging purposes")
@click.option(
    "--interactive", help="If passed, then for each output field will ask user interactively to enter the "
                          "description. By default is interactive mode is disabled", is_flag=True)
def json_to_outputs_command(**kwargs):
    json_to_outputs(**kwargs)


# ====================== generate-test-playbook ====================== #
@main.command(name="generate-test-playbook",
              short_help="Generate test playbook from integration or script")
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
    help='Specify output directory')
@click.option(
    '-n', '--name',
    required=True,
    help='Specify test playbook name')
@click.option(
    '--no-outputs', is_flag=True,
    help='Skip generating verification conditions for each output contextPath. Use when you want to decide which '
         'outputs to verify and which not')
@click.option(
    "-v", "--verbose", help="Verbose output for debug purposes - shows full exception stack trace", is_flag=True)
def generate_test_playbook(**kwargs):
    file_type: FileType = find_type(kwargs.get('input', ''), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT]:
        print_error('Generating test playbook is possible only for an Integration or a Script.')
        return 1
    generator = PlaybookTestsGenerator(file_type=file_type.value, **kwargs)
    generator.run()


# ====================== init ====================== #
@main.command(name="init", short_help="Initialize a new Pack, Integration or Script."
                                      " If the script/integration flags are not present"
                                      " then we will create a pack with the given name."
                                      " Otherwise when using the flags we will generate"
                                      " a script/integration based on your selection.")
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-n", "--name", help="The name of the directory and file you want to create", required=True)
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
                             "Integration template options: HelloWorld, HelloIAMWorld\n"
                             "Script template options: HelloWorldScript")
@click.option(
    '--demisto_mock', is_flag=True,
    help="Copy the demistomock. Relevant for initialization of Scripts and Integrations within a Pack.")
@click.option(
    '--common_server', is_flag=True,
    help="Copy the CommonServerPython. Relevant for initialization of Scripts and Integrations within a Pack.")
def init(**kwargs):
    initiator = Initiator(**kwargs)
    initiator.init()
    return 0


# ====================== generate-docs ====================== #
@main.command(name="generate-docs",
              short_help="Generate documentation for integration, playbook or script from yaml file.")
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
                            "e.g (xdr-get-incidents,xdr-update-incident",
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
    "-cp", "--command_permissions", help="Path for file containing commands permissions"
                                         " Each command permissions should be in a separate line."
                                         " (i.e. '<command-name> Administrator READ-WRITE')", required=False)
@click.option(
    "-l", "--limitations", help="Known limitations. Number the steps by '*' (i.e. '* foo. * bar.')", required=False)
@click.option(
    "--insecure", help="Skip certificate validation to run the commands in order to generate the docs.",
    is_flag=True)
@click.option(
    "-v", "--verbose", is_flag=True, help="Verbose output - mainly for debugging purposes.")
def generate_doc(**kwargs):
    input_path: str = kwargs.get('input', '')
    output_path = kwargs.get('output')
    command = kwargs.get('command')
    examples = str(kwargs.get('examples', ''))
    permissions = kwargs.get('permissions')
    limitations = kwargs.get('limitations')
    insecure: bool = kwargs.get('insecure', False)
    verbose: bool = kwargs.get('verbose', False)

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

    print(f'Start generating {file_type.value} documentation...')
    if file_type == FileType.INTEGRATION:
        use_cases = kwargs.get('use_cases')
        command_permissions = kwargs.get('command_permissions')
        return generate_integration_doc(input_path=input_path, output=output_path, use_cases=use_cases,
                                        examples=examples, permissions=permissions,
                                        command_permissions=command_permissions, limitations=limitations,
                                        insecure=insecure, verbose=verbose, command=command)
    elif file_type == FileType.SCRIPT:
        return generate_script_doc(input_path=input_path, output=output_path, examples=examples, permissions=permissions,
                                   limitations=limitations, insecure=insecure, verbose=verbose)
    elif file_type == FileType.PLAYBOOK:
        return generate_playbook_doc(input_path=input_path, output=output_path, permissions=permissions,
                                     limitations=limitations, verbose=verbose)
    else:
        print_error(f'File type {file_type.value} is not supported.')
        return 1


# ====================== create-id-set ====================== #
@main.command(name="create-id-set",
              hidden=True,
              short_help='''Create the content dependency tree by ids.''')
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i', '--input', help='Input file path, the default is the content repo.', default='', required=False)
@click.option(
    "-o", "--output", help="Output file path, the default is the Tests directory.", default='', required=False)
def id_set_command(**kwargs):
    id_set_creator = IDSetCreator(**kwargs)
    id_set_creator.create_id_set()


@main.command(name='merge-id-sets',
              hidden=True,
              short_help='Merge two id_sets')
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-i1', '--id-set1', help='First id_set.json file path', required=True
)
@click.option(
    '-i2', '--id-set2', help='Second id_set.json file path', required=True
)
@click.option(
    '-o', '--output', help='File path of the united id_set', required=True
)
def merge_id_sets_command(**kwargs):
    first = kwargs['id_set1']
    second = kwargs['id_set2']
    output = kwargs['output']

    _, duplicates = merge_id_sets_from_files(
        first_id_set_path=first,
        second_id_set_path=second,
        output_id_set_path=output
    )
    if duplicates:
        print_error(f'Failed to merge ID sets: {first} with {second}, '
                    f'there are entities with ID: {duplicates} that exist in both ID sets')
        sys.exit(1)


# ====================== update-release-notes =================== #
@main.command(name="update-release-notes",
              short_help='''Auto-increment pack version and generate release notes template.''')
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input", help="The relative path of the content pack. For example Packs/Pack_Name"
)
@click.option(
    '-u', '--update_type', help="The type of update being done. [major, minor, revision, maintenance, documentation]",
    type=click.Choice(['major', 'minor', 'revision', 'maintenance', 'documentation'])
)
@click.option(
    '-v', '--version', help="Bump to a specific version."
)
@click.option(
    '--all', help="Update all changed packs", is_flag=True
)
@click.option(
    '--text', help="Text to add to all of the release notes files",
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
def update_pack_releasenotes(**kwargs):
    _pack = kwargs.get('input')
    update_type = kwargs.get('update_type')
    pre_release: bool = kwargs.get('pre_release', False)
    is_all = kwargs.get('all')
    text: str = kwargs.get('text', '')
    specific_version = kwargs.get('version')
    id_set_path = kwargs.get('id_set_path')
    prev_ver = kwargs.get('prev_ver') if kwargs.get('prev_ver') else 'origin/master'
    prev_rn_text = ''
    # _pack can be both path or pack name thus, we extract the pack name from the path if beeded.
    if _pack and is_all:
        print_error("Please remove the --all flag when specifying only one pack.")
        sys.exit(0)
    print("Starting to update release notes.")
    if _pack and '/' in _pack:
        _pack = get_pack_name(_pack)
    try:
        validate_manager = ValidateManager(skip_pack_rn_validation=True, prev_ver=prev_ver)
        validate_manager.setup_git_params()
        modified, added, old, changed_meta_files, _packs = validate_manager.get_modified_and_added_files(
            '...', prev_ver)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError, FileNotFoundError):
        print_error("You are not running `demisto-sdk update-release-notes` command in the content repository.\n"
                    "Please run `cd content` from your terminal and run the command again")
        sys.exit(1)

    packs_existing_rn = {}
    for file_path in added:
        if 'ReleaseNotes' in file_path:
            packs_existing_rn[get_pack_name(file_path)] = file_path

    filterd_modified = filter_files_by_type(modified, skip_file_types=SKIP_RELEASE_NOTES_FOR_TYPES)
    filterd_added = filter_files_by_type(added, skip_file_types=SKIP_RELEASE_NOTES_FOR_TYPES)

    if _pack and API_MODULES_PACK in _pack:
        # case: ApiModules
        update_api_modules_dependents_rn(_pack, pre_release, update_type, added, modified,
                                         id_set_path=id_set_path, text=text)

    # create release notes:
    if _pack:
        _packs = {_pack}
    elif not is_all and len(_packs) > 1:
        # case: multiple packs
        pack_list = ' ,'.join(_packs)
        print_error(f"Detected changes in the following packs: {pack_list.rstrip(', ')}\n"
                    f"To update release notes in a specific pack, please use the -i parameter "
                    f"along with the pack name.")
        sys.exit(0)
    if _packs:
        for pack in _packs:
            if pack in packs_existing_rn and update_type is None:
                try:
                    with open(packs_existing_rn[pack], 'r') as f:
                        prev_rn_text = f.read()
                except Exception as e:
                    print_error(f'Failed to load the previous release notes file content: {e}')
            elif pack in packs_existing_rn and update_type is not None:
                print_error(f"New release notes file already found for {pack}. "
                            f"Please update manually or run `demisto-sdk update-release-notes "
                            f"-i {pack}` without specifying the update_type.")
                continue

            pack_modified = filter_files_on_pack(pack, filterd_modified)
            pack_added = filter_files_on_pack(pack, filterd_added)
            pack_old = filter_files_on_pack(pack, old)

            # default case:
            if pack_modified or pack_added or pack_old:
                update_pack_rn = UpdateRN(pack_path=f'Packs/{pack}', update_type=update_type,
                                          modified_files_in_pack=pack_modified.union(pack_old), pre_release=pre_release,
                                          added_files=pack_added, specific_version=specific_version, text=text,
                                          prev_rn_text=prev_rn_text)
                updated = update_pack_rn.execute_update()
                # if new release notes were created and if previous release notes existed, remove previous
                if updated and prev_rn_text:
                    os.unlink(packs_existing_rn[pack])

            else:
                print_warning(f'Either no cahnges were found in {pack} pack '
                              f'or the changes found should not be documented in the release notes file '
                              f'If relevant changes were made, please commit the changes and rerun the command')
    else:
        print_warning('No changes that require release notes were detected. If such changes were made, '
                      'please commit the changes and rerun the command')
    sys.exit(0)


# ====================== find-dependencies ====================== #
@main.command(name="find-dependencies",
              short_help='''Find pack dependencies and update pack metadata.''')
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input", help="Pack path to find dependencies. For example: Pack/HelloWorld", required=True,
    type=click.Path(exists=True, dir_okay=True))
@click.option(
    "-idp", "--id-set-path", help="Path to id set json file.", required=False)
@click.option(
    "--no-update", help="Use to find the pack dependencies without updating the pack metadata.", required=False,
    is_flag=True)
@click.option('-v', "--verbose", help="Whether to print the log to the console.", required=False,
              is_flag=True)
def find_dependencies_command(id_set_path, verbose, no_update, **kwargs):
    update_pack_metadata = not no_update
    input_path: Path = kwargs["input"]  # To not shadow python builtin `input`
    try:
        assert "Packs/" in str(input_path)
        pack_name = str(input_path).replace("Packs/", "")
        assert "/" not in str(pack_name)
    except AssertionError:
        print_error("Input path is not a pack. For example: Packs/HelloWorld")
        sys.exit(1)
    try:
        PackDependencies.find_dependencies(pack_name=pack_name,
                                           id_set_path=id_set_path,
                                           verbose=verbose,
                                           update_pack_metadata=update_pack_metadata,
                                           )
    except ValueError as exp:
        print_error(str(exp))


# ====================== openapi-codegen ====================== #
@main.command(name="openapi-codegen",
              short_help='''Generates a Cortex XSOAR integration given an OpenAPI specification file.''',
              help='''Generates a Cortex XSOAR integration given an OpenAPI specification file.
               In the first run of the command, an integration configuration file is created, which can be modified.
               Then, the command is run a second time with the integration configuration to
               generate the actual integration files.''')
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
def openapi_codegen_command(**kwargs):
    if not kwargs.get('output_dir'):
        output_dir = os.getcwd()
    else:
        output_dir = kwargs['output_dir']

    # Check the directory exists and if not, try to create it
    if not os.path.exists(output_dir):
        try:
            os.mkdir(output_dir)
        except Exception as err:
            tools.print_error(f'Error creating directory {output_dir} - {err}')
            sys.exit(1)
    if not os.path.isdir(output_dir):
        tools.print_error(f'The directory provided "{output_dir}" is not a directory')
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
        tools.print_success(f'Created configuration file in {output_dir}')
        if not kwargs.get('use_default', False):
            config_path = os.path.join(output_dir, f'{base_name}.json')
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
        tools.print_success(f'Successfully finished generating integration code and saved it in {output_dir}')
    else:
        tools.print_error(f'There was an error creating the package in {output_dir}')
        sys.exit(1)


# ====================== test-content command ====================== #
@main.command(name="test-content",
              short_help='''
              Created incidents for selected test-playbooks and gives a report about the results''',
              help='''Configure instances for the integration needed to run tests_to_run tests.
              Run test module on each integration.
              create an investigation for each test.
              run test playbook on the created investigation using mock if possible.
              Collect the result and give a report.''',
              hidden=True)
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
    execute_test_content(**kwargs)


@main.resultcallback()
def exit_from_program(result=0, **kwargs):
    sys.exit(result)


# todo: add download from demisto command


if __name__ == '__main__':
    sys.exit(main())
