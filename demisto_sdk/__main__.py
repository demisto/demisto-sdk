# Site packages
import os
import re
import sys

from pkg_resources import get_distribution

# Third party packages
import click
import demisto_sdk.commands.common.tools as tools
from demisto_sdk.commands.common.configuration import Configuration
# Common tools
from demisto_sdk.commands.common.tools import (find_type,
                                               get_last_remote_release_version,
                                               get_pack_name, print_error,
                                               print_warning)
from demisto_sdk.commands.create_artifacts.content_creator import \
    ContentCreator
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
# Import demisto-sdk commands
from demisto_sdk.commands.run_cmd.runner import Runner
from demisto_sdk.commands.run_playbook.playbook_runner import PlaybookRunner
from demisto_sdk.commands.secrets.secrets import SecretsValidator
from demisto_sdk.commands.split_yml.extractor import Extractor
from demisto_sdk.commands.unify.unifier import Unifier
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
from demisto_sdk.commands.upload.uploader import Uploader
from demisto_sdk.commands.validate.file_validator import FilesValidator


class DemistoSDK:
    """
    The core class for the SDK.
    """

    def __init__(self):
        self.configuration = None


class RNInputValidation(click.ParamType):
    name = 'update_type'

    def validate_rn_input(self, value, param, ctx):
        if value:
            if re.match(r'(?i)(?<=|^)major(?= |$)', value):
                update_type = 'major'
            elif re.match(r'(?i)(?<=|^)minor(?= |$)', value):
                update_type = 'minor'
            elif re.match(r'(?i)(?<=|^)revision(?= |$)', value):
                update_type = 'revision'
            else:
                self.fail(
                    f'{value} is not a valid option. Please select: major, minor, revision',
                    param,
                    ctx,
                )
        else:
            update_type = None
        return update_type


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
    file_type = find_type(kwargs.get('input'))
    if file_type not in ["integration", "script"]:
        print_error('File is not an Integration or Script.')
        return 1
    extractor = Extractor(configuration=config.configuration, file_type=file_type, **kwargs)
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
    file_type = find_type(kwargs.get('input'))
    if file_type not in ["integration", "script"]:
        print_error('File is not an Integration or Script.')
        return 1
    extractor = Extractor(configuration=config.configuration, file_type=file_type, **kwargs)
    return extractor.extract_code(kwargs['outfile'])


# ====================== unify ====================== #
@main.command(name="unify",
              short_help='Unify code, image, description and yml files to a single Demisto yml file. Note that '
                         'this should be used on a single integration/script and not a pack '
                         'not multiple scripts/integrations')
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input", help="The path to the files to unify", required=True
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
    unifier = Unifier(**kwargs)
    unifier.merge_script_package_to_yml()
    return 0


# ====================== validate ====================== #
@main.command(name="validate",
              short_help='Validate your content files.')
@click.help_option(
    '-h', '--help'
)
@click.option(
    '--no-conf-json', is_flag=True,
    default=False, show_default=True, help='Skip conf.json validation')
@click.option(
    '-s', '--id-set', is_flag=True,
    default=False, show_default=True, help='Validate the id_set file.')
@click.option(
    '--prev-ver', help='Previous branch or SHA1 commit to run checks against.')
@click.option(
    '--post-commit',
    is_flag=True,
    help='Whether the validation should run only on the current branch\'s committed changed files. '
         'This applies only when the -g flag is supplied.')
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
    '-p', '--path', help='Path of file to validate specifically, outside of a git directory.', hidden=True
)
@click.option(
    '-a', '--validate-all', is_flag=True, show_default=True, default=False,
    help='Whether to run all validation on all files or not'
)
@click.option(
    '-i', '--input', help='The path of the content pack/file to validate specifically.'
)
@click.option(
    '--skip-pack-release-notes', is_flag=True,
    help='Skip validation of pack release notes.')
@click.option(
    '--print-ignored-errors', is_flag=True,
    help='Print ignored errors as warnings.')
@pass_config
def validate(config, **kwargs):
    sys.path.append(config.configuration.env_dir)

    file_path = kwargs['path'] or kwargs['input']
    if file_path and not os.path.isfile(file_path) and not os.path.isdir(file_path):
        print_error(f'File {file_path} was not found')
        return 1
    else:
        is_private_repo = tools.is_private_repository()

        validator = FilesValidator(configuration=config.configuration,
                                   is_backward_check=not kwargs['no_backward_comp'],
                                   only_committed_files=kwargs['post_commit'], prev_ver=kwargs['prev_ver'],
                                   skip_conf_json=kwargs['no_conf_json'], use_git=kwargs['use_git'],
                                   file_path=file_path,
                                   validate_all=kwargs.get('validate_all'),
                                   validate_id_set=kwargs['id_set'],
                                   skip_pack_rn_validation=kwargs['skip_pack_release_notes'],
                                   print_ignored_errors=kwargs['print_ignored_errors'],
                                   is_private_repo=is_private_repo, )
        return validator.run()


# ====================== create-content-artifacts ====================== #
@main.command(
    name="create-content-artifacts",
    hidden=True,
    short_help='Create content artifacts. This will generate content_new.zip file which can be used to '
               'upload to your server in order to upload a whole new content version to your Demisto '
               'instance.',
)
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-a', '--artifacts_path', help='The path of the directory in which you want to save the created content artifacts')
@click.option(
    '-v', '--content_version', default='', help='The content version which you want to appear in CommonServerPython.')
@click.option(
    '-p', '--preserve_bundles', is_flag=True, default=False, show_default=True,
    help='Keep the bundles created in the process of making the content artifacts')
@click.option(
    '--no-update-commonserver', is_flag=True, help='Whether to update CommonServerPython or not - used for local runs.'
)
@click.option(
    '--packs', is_flag=True,
    help='If passed, will create only content_packs.zip'
)
def create(**kwargs):
    content_creator = ContentCreator(**kwargs)
    return content_creator.run()


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
@pass_config
def secrets(config, **kwargs):
    sys.path.append(config.configuration.env_dir)
    secrets = SecretsValidator(configuration=config.configuration, is_circle=kwargs['post_commit'],
                               ignore_entropy=kwargs['ignore_entropy'], white_list_path=kwargs['whitelist'],
                               input_path=kwargs.get('input'))
    return secrets.run()


# ====================== lint ====================== #
@main.command(name="lint",
              short_help="Lint command will perform:\n 1. Package in host checks - flake8, bandit, mypy, vulture.\n 2. "
                         "Package in docker image checks -  pylint, pytest, powershell - test, powershell - analyze.\n "
                         "Meant to be used with integrations/scripts that use the folder (package) structure. Will lookup up what"
                         "docker image to use and will setup the dev dependencies and file in the target folder. ")
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
@click.option("--no-mypy", is_flag=True, help="Do NOT run mypy static type checking")
@click.option("--no-vulture", is_flag=True, help="Do NOT run vulture linter")
@click.option("--no-pylint", is_flag=True, help="Do NOT run pylint linter")
@click.option("--no-test", is_flag=True, help="Do NOT test (skip pytest)")
@click.option("--no-pwsh-analyze", is_flag=True, help="Do NOT run powershell analyze")
@click.option("--no-pwsh-test", is_flag=True, help="Do NOT run powershell test")
@click.option("-kc", "--keep-container", is_flag=True, help="Keep the test container")
@click.option("--test-xml", help="Path to store pytest xml results", type=click.Path(exists=True, resolve_path=True))
@click.option("--failure-report", help="Path to store failed packs report", type=click.Path(exists=True, resolve_path=True))
@click.option("-lp", "--log-path", help="Path to store all levels of logs",
              type=click.Path(exists=True, resolve_path=True))
def lint(input: str, git: bool, all_packs: bool, verbose: int, quiet: bool, parallel: int, no_flake8: bool,
         no_bandit: bool, no_mypy: bool, no_vulture: bool, no_pylint: bool, no_test: bool, no_pwsh_analyze: bool,
         no_pwsh_test: bool, keep_container: bool, test_xml: str, failure_report: str, log_path: str):
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
                               log_path=log_path)
    return lint_manager.run_dev_packages(parallel=parallel,
                                         no_flake8=no_flake8,
                                         no_bandit=no_bandit,
                                         no_mypy=no_mypy,
                                         no_vulture=no_vulture,
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
                         "incidenttype/indicatortype/layout/dashboard file. ")
@click.help_option(
    '-h', '--help')
@click.option(
    "-i", "--input", help="The path of the script yml file", type=click.Path(exists=True, resolve_path=True))
@click.option(
    "-o", "--output", help="The path where the formatted file will be saved to",
    type=click.Path(resolve_path=True))
@click.option(
    "-fv", "--from-version", help="Specify fromversion of the pack")
@click.option(
    "-nv", "--no-validate", help="Set when validate on file is not wanted", is_flag=True)
def format_yml(input=None, output=None, from_version=None, no_validate=None):
    return format_manager(input, output, from_version, no_validate)


# ====================== upload ====================== #
@main.command(name="upload",
              short_help="Upload integration to Demisto instance. DEMISTO_BASE_URL environment variable should contain"
                         " the Demisto server base URL. DEMISTO_API_KEY environment variable should contain a valid "
                         "Demisto API Key.")
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
    "-i", "--input", help="Valid JSON file path. If not specified then script will wait for user input in the terminal",
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
    file_type = find_type(kwargs.get('input'))
    if file_type not in ["integration", "script"]:
        print_error('Generating test playbook is possible only for an Integration or a Script.')
        return 1
    generator = PlaybookTestsGenerator(file_type=file_type, **kwargs)
    generator.run()


# ====================== init ====================== #
@main.command(name="init", short_help="Initiate a new Pack, Integration or Script."
                                      " If the script/integration flags are not present"
                                      " then we will create a pack with the given name."
                                      " Otherwise when using the flags we will generate"
                                      " a script/integration based on your selection.")
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
    '--integration', is_flag=True, help="Create an Integration based on HelloWorld example")
@click.option(
    '--script', is_flag=True, help="Create a script based on HelloWorldScript example")
@click.option(
    "--pack", is_flag=True, help="Create pack and its sub directories")
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
    "-e", "--examples", help="Path for file containing command or script examples."
                             " Each Command should be in a separate line."
                             " For script - the script example surrounded by double quotes.")
@click.option(
    "-p", "--permissions", type=click.Choice(["none", "general", "per-command"]), help="Permissions needed.",
    required=True, default='none')
@click.option(
    "-cp", "--command_permissions", help="Path for file containing commands permissions"
                                         " Each command permissions should be in a separate line."
                                         " (i.e. '!command-name Administrator READ-WRITE')", required=False)
@click.option(
    "-l", "--limitations", help="Known limitations. Number the steps by '*' (i.e. '* foo. * bar.')", required=False)
@click.option(
    "--insecure", help="Skip certificate validation to run the commands in order to generate the docs.",
    is_flag=True)
@click.option(
    "-v", "--verbose", is_flag=True, help="Verbose output - mainly for debugging purposes.")
def generate_doc(**kwargs):
    input_path = kwargs.get('input')
    output_path = kwargs.get('output')
    command = kwargs.get('command')
    examples = kwargs.get('examples')
    permissions = kwargs.get('permissions')
    limitations = kwargs.get('limitations')
    insecure = kwargs.get('insecure')
    verbose = kwargs.get('verbose')

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
        if output_path and (not os.path.isfile(os.path.join(output_path, "README.md")))\
                or (not output_path)\
                and (not os.path.isfile(os.path.join(os.path.dirname(os.path.realpath(input_path)), "README.md"))):
            print_error("The `command` argument must be presented with existing `README.md` docs.")
            return 1

    file_type = find_type(kwargs.get('input', ''))
    if file_type not in ["integration", "script", "playbook"]:
        print_error('File is not an Integration, Script or a Playbook.')
        return 1

    print(f'Start generating {file_type} documentation...')
    if file_type == 'integration':
        use_cases = kwargs.get('use_cases')
        command_permissions = kwargs.get('command_permissions')
        return generate_integration_doc(input=input_path, output=output_path, use_cases=use_cases,
                                        examples=examples, permissions=permissions,
                                        command_permissions=command_permissions, limitations=limitations,
                                        insecure=insecure, verbose=verbose, command=command)
    elif file_type == 'script':
        return generate_script_doc(input=input_path, output=output_path, examples=examples, permissions=permissions,
                                   limitations=limitations, insecure=insecure, verbose=verbose)
    elif file_type == 'playbook':
        return generate_playbook_doc(input=input_path, output=output_path, permissions=permissions,
                                     limitations=limitations, verbose=verbose)
    else:
        print_error(f'File type {file_type} is not supported.')
        return 1


# ====================== create-id-set ====================== #
@main.command(name="create-id-set",
              hidden=True,
              short_help='''Create the content dependency tree by ids.''')
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-o", "--output", help="Output file path, the default is the Tests directory.", required=False)
def id_set_command(**kwargs):
    id_set_creator = IDSetCreator(**kwargs)
    id_set_creator.create_id_set()


# ====================== update-release-notes =================== #
@main.command(name="update-release-notes",
              short_help='''Auto-increment pack version and generate release notes template.''')
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-p", "--pack", help="Name of the pack."
)
@click.option(
    '-u', '--update_type', help="The type of update being done. [major, minor, revision]",
    type=RNInputValidation()
)
@click.option(
    '--all', help="Update all changed packs", is_flag=True
)
@click.option(
    "--pre_release", help="Indicates that this change should be designated a pre-release version.",
    is_flag=True)
def update_pack_releasenotes(**kwargs):
    _pack = kwargs.get('pack')
    update_type = kwargs.get('update_type')
    pre_release = kwargs.get('pre_release')
    is_all = kwargs.get('all')
    modified, added, old, _packs = FilesValidator(use_git=True).get_modified_and_added_files()
    packs_existing_rn = set()
    for pf in added:
        if 'ReleaseNotes' in pf:
            pack_with_existing_rn = get_pack_name(pf)
            packs_existing_rn.add(pack_with_existing_rn)
    if len(packs_existing_rn):
        existing_rns = ''.join(f"{p}, " for p in packs_existing_rn)
        print_warning(f"Found existing release notes for the following packs: {existing_rns.rstrip(', ')}")
    if len(_packs) > 1:
        pack_list = ''.join(f"{p}, " for p in _packs)
        if not is_all:
            if _pack:
                pass
            else:
                print_error(f"Detected changes in the following packs: {pack_list.rstrip(', ')}\n"
                            f"To update release notes in a specific pack, please use the -p parameter "
                            f"along with the pack name.")
                sys.exit(0)
    if len(modified) < 1:
        print_warning('No changes were detected.')
        sys.exit(0)
    if is_all and not _pack:
        packs = list(_packs - packs_existing_rn)
        packs_list = ''.join(f"{p}, " for p in packs)
        print_warning(f"Adding release notes to the following packs: {packs_list.rstrip(', ')}")
        for pack in packs:
            update_pack_rn = UpdateRN(pack=pack, update_type=update_type, pack_files=modified,
                                      pre_release=pre_release, added_files=added)
            update_pack_rn.execute_update()
    elif is_all and _pack:
        print_error("Please remove the --all flag when specifying only one pack.")
        sys.exit(0)
    else:
        if _pack:
            if _pack in packs_existing_rn and update_type is not None:
                print_error(f"New release notes file already found for {_pack}. "
                            f"Please update manually or run `demisto-sdk update-release-notes "
                            f"-p {_pack}` without specifying the update_type.")
            else:
                update_pack_rn = UpdateRN(pack=_pack, update_type=update_type, pack_files=modified,
                                          pre_release=pre_release, added_files=added)
                update_pack_rn.execute_update()


# ====================== find-dependencies ====================== #
@main.command(name="find-dependencies",
              short_help='''Find pack dependencies and update pack metadata.''')
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-p", "--pack_folder_name", help="Pack folder name to find dependencies.", required=True)
@click.option(
    "-i", "--id_set_path", help="Path to id set json file.", required=False)
def find_dependencies_command(**kwargs):
    pack_name = kwargs.get('pack_folder_name', '')
    id_set_path = kwargs.get('id_set_path')
    PackDependencies.find_dependencies(pack_name=pack_name, id_set_path=id_set_path)


@main.resultcallback()
def exit_from_program(result=0, **kwargs):
    sys.exit(result)


# todo: add download from demisto command


if __name__ == '__main__':
    sys.exit(main())
