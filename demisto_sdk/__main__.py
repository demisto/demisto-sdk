# Site packages
import os
from pkg_resources import get_distribution
import sys

# Third party packages
import click

# Import demisto-sdk commands
from demisto_sdk.commands.run_cmd.runner import Runner
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.unify.unifier import Unifier
from demisto_sdk.commands.upload.uploader import Uploader
from demisto_sdk.commands.init.initiator import Initiator
from demisto_sdk.commands.split_yml.extractor import Extractor
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.lint.lint_manager import LintManager
from demisto_sdk.commands.secrets.secrets import SecretsValidator
from demisto_sdk.commands.run_playbook.playbook_runner import PlaybookRunner
from demisto_sdk.commands.validate.file_validator import FilesValidator
from demisto_sdk.commands.create_artifacts.content_creator import ContentCreator
from demisto_sdk.commands.json_to_outputs.json_to_outputs import json_to_outputs
from demisto_sdk.commands.generate_test_playbook.test_playbook_generator import PlaybookTestsGenerator
from demisto_sdk.commands.generate_docs.generate_integration_doc import generate_integration_doc
from demisto_sdk.commands.generate_docs.generate_script_doc import generate_script_doc
from demisto_sdk.commands.generate_docs.generate_playbook_doc import generate_playbook_doc
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator

# Common tools
from demisto_sdk.commands.common.tools import print_error, print_warning, get_last_remote_release_version, find_type


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
        print(version)


# ====================== extract ====================== #
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
    help="Don't add an import for CommonServerPython."
         "If not specified will import unless this is CommonServerPython",
    is_flag=True,
    show_default=True
)
@pass_config
def extract(config, **kwargs):
    file_type = find_type(kwargs.get('input'))
    if file_type not in ["integration", "script"]:
        print_error(F'File is not an Integration or Script.')
        return 1
    extractor = Extractor(configuration=config.configuration, file_type=file_type, **kwargs)
    return extractor.extract_to_package_format()


# ====================== extract-code ====================== #
@main.command(name="extract-code",
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
        print_error(F'File is not an Integration or Script.')
        return 1
    extractor = Extractor(configuration=config.configuration, file_type=file_type, **kwargs)
    return extractor.extract_code(kwargs['outfile'])


# ====================== unify ====================== #
@main.command(name="unify",
              short_help='Unify code, image, description and yml files to a single Demisto yml file.')
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
# TODO: add a configuration for conf.json and id_set.json
@main.command(name="validate",
              short_help='Validate your content files.')
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-j', '--conf-json', is_flag=True,
    default=False, show_default=True, help='Validate the conf.json file.')
@click.option(
    '--prev-ver', help='Previous branch or SHA1 commit to run checks against.')
@click.option(
    '--post-commit', is_flag=True, help='Whether the validation is done after you committed your files, '
                                        'this will help the command to determine which files it should check in its '
                                        'run. Before you commit the files it should not be used. Mostly for build '
                                        'validations.')
@click.option(
    '--no-backward-comp', is_flag=True, show_default=True,
    help='Whether to check backward compatibility or not.')
@click.option(
    '-g', '--use-git', is_flag=True, show_default=True,
    default=False, help='Validate changes using git - this will check your branch changes and will run only on them.')
@click.option(
    '-p', '--path', help='Path of file to validate specifically, outside of a git directory.'
)
@pass_config
def validate(config, **kwargs):
    sys.path.append(config.configuration.env_dir)

    file_path = kwargs['path']

    if file_path and not os.path.isfile(file_path):
        print_error(F'File {file_path} was not found')
        return 1
    else:
        validator = FilesValidator(configuration=config.configuration,
                                   is_backward_check=not kwargs['no_backward_comp'],
                                   is_circle=kwargs['post_commit'], prev_ver=kwargs['prev_ver'],
                                   validate_conf_json=kwargs['conf_json'], use_git=kwargs['use_git'],
                                   file_path=kwargs.get('path'))
        return validator.run()


# ====================== create ====================== #
@main.command(name="create-content-artifacts",
              short_help='Create content artifacts. This will generate content_new.zip file which can be used to '
                         'upload to your server in order to upload a whole new content version to your Demisto '
                         'instance.')
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
                               ignore_entropy=kwargs['ignore_entropy'], white_list_path=kwargs['whitelist'])
    return secrets.run()


# ====================== lint ====================== #
@main.command(name="lint",
              short_help="Run lintings (flake8, mypy, pylint, bandit, vulture) and pytest. pylint and pytest will run "
                         "within the docker image of an integration/script. Meant to be used with integrations/scripts "
                         "that use the folder (package) structure. Will lookup up what docker image to use and will "
                         "setup the dev dependencies and file in the target folder. ")
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-d", "--dir", help="Specify directory of integration/script")
@click.option(
    "--no-pylint", is_flag=True, help="Do NOT run pylint linter")
@click.option(
    "--no-mypy", is_flag=True, help="Do NOT run mypy static type checking")
@click.option(
    "--no-flake8", is_flag=True, help="Do NOT run flake8 linter")
@click.option(
    "--no-bandit", is_flag=True, help="Do NOT run bandit linter")
@click.option(
    "--no-vulture", is_flag=True, help="Do NOT run vulture linter")
@click.option(
    "--no-test", is_flag=True, help="Do NOT test (skip pytest)")
@click.option(
    "-r", "--root", is_flag=True, help="Run pytest container with root user")
@click.option(
    "-k", "--keep-container", is_flag=True, help="Keep the test container")
@click.option(
    "-v", "--verbose", is_flag=True, help="Verbose output - mainly for debugging purposes")
@click.option(
    "--cpu-num",
    help="Number of CPUs to run pytest on (can set to `auto` for automatic detection of the number of CPUs)",
    default=0)
@click.option(
    "-p", "--parallel", is_flag=True, help="Run tests in parallel")
@click.option(
    "-m", "--max-workers", type=int, help="How many threads to run in parallel")
@click.option(
    "-g", "--git", is_flag=True, help="Will run only on changed packages")
@click.option(
    "-a", "--run-all-tests", is_flag=True, help="Run lint on all directories in content repo")
@click.option(
    "--outfile", help="Save failing packages to a file"
)
@pass_config
def lint(config, dir, **kwargs):
    linter = LintManager(configuration=config.configuration, project_dir_list=dir, **kwargs)
    return linter.run_dev_packages()


# ====================== format ====================== #
@main.command(name="format",
              short_help="Run formatter on a given script/playbook/integration yml file. ")
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-t", "--file-type", type=click.Choice(["integration", "script", "playbook"]),
    help="The type of yml file to be formatted.")
@click.option(
    "-s", "--source-file", help="The path of the script yml file")
@click.option(
    "-o", "--output-file-name", help="The path where the formatted file will be saved to")
@click.option(
    '-g', '--use-git', is_flag=True, show_default=True,
    default=False, help='Format changed files using git'
                        '- this will format your branch changes and will run only on them.')
def format_yml(use_git=False, file_type=None, **kwargs):
    return format_manager(use_git, file_type, **kwargs)


@main.command(name="upload",
              short_help="Upload integration to Demisto instance. DEMISTO_BASE_URL environment variable should contain"
                         " the Demisto server base URL. DEMISTO_API_KEY environment variable should contain a valid "
                         "Demisto API Key.")
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-i", "--input", help="The path of an integration file or a package directory to upload", required=True)
@click.option(
    "--insecure", help="Skip certificate validation", is_flag=True)
@click.option(
    "-v", "--verbose", help="Verbose output", is_flag=True)
def upload(**kwargs):
    uploader = Uploader(**kwargs)
    return uploader.upload()


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
        print_error(F'Generating test playbook is possible only for an Integration or a Script.')
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
@click.option("--pack", is_flag=True, help="Create pack and its sub directories")
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

    file_type = find_type(kwargs.get('input', ''))
    if file_type not in ["integration", "script", "playbook"]:
        print_error(F'File is not an Integration, Script or a Playbook.')
        return 1

    print(f'Start generating {file_type} documentation...')
    if file_type == 'integration':
        return generate_integration_doc(**kwargs)
    elif file_type == 'script':
        return generate_script_doc(**kwargs)
    elif file_type == 'playbook':
        return generate_playbook_doc(**kwargs)
    else:
        print_error(f'File type {file_type} is not supported.')
        return 1


@main.command(name="create-id-set",
              short_help='''Create the content dependency tree by ids.''')
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-o", "--output", help="Output file path, the default is the Tests directory.", required=False)
def id_set_command(**kwargs):
    id_set_creator = IDSetCreator(**kwargs)
    id_set_creator.create_id_set()


@main.resultcallback()
def exit_from_program(result=0, **kwargs):
    sys.exit(result)

# todo: add download from demisto command


if __name__ == '__main__':
    sys.exit(main())
