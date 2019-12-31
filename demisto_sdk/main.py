import sys
import click
from pkg_resources import get_distribution

from demisto_sdk.core import DemistoSDK
from demisto_sdk.common.tools import str2bool
from demisto_sdk.yaml_tools.unifier import Unifier
from demisto_sdk.yaml_tools.extractor import Extractor
from demisto_sdk.common.configuration import Configuration
from demisto_sdk.dev_tools.lint_manager import LintManager
from demisto_sdk.dev_tools.spell_checker import SpellCheck
from demisto_sdk.validation.secrets import SecretsValidator
from demisto_sdk.validation.file_validator import FilesValidator
from demisto_sdk.yaml_tools.update_script import ScriptYMLFormat
from demisto_sdk.yaml_tools.content_creator import ContentCreator
from demisto_sdk.yaml_tools.update_playbook import PlaybookYMLFormat
from demisto_sdk.yaml_tools.update_integration import IntegrationYMLFormat
from demisto_sdk.common.constants import SCRIPT_PREFIX, INTEGRATION_PREFIX


pass_config = click.make_pass_decorator(DemistoSDK, ensure=True)


@click.group(invoke_without_command=True, no_args_is_help=True, context_settings=dict(max_content_width=500), )
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-d', '--env-dir', help='Specify a working directory.'
)
@click.option(
    '-v', '--version', help='Get the demisto-sdk version.',
    is_flag=True, default=False
)
@pass_config
def main(config, version, env_dir):
    config.configuration = Configuration()
    if version:
        version = get_distribution('demisto-sdk').version
        print(version)

    if env_dir:
        config.configuration.env_dir = env_dir


@main.command(name="extract",
              short_help="Extract code, image and description files from a Demisto integration or script yaml file.")
@click.help_option(
    '-h', '--help'
)
@click.option(
    '--infile', '-i',
    help='The yml file to extract from',
    required=True
)
@click.option(
    '--outfile', '-o',
    required=True,
    help="The output dir to write the extracted code/description/image to."
)
@click.option(
    '--yml-type', '-y',
    help="Yaml type. If not specified will try to determine type based upon path.",
    type=click.Choice([SCRIPT_PREFIX, INTEGRATION_PREFIX])
)
@click.option(
    '--demisto-mock', '-d',
    help="Add an import for demisto mock, true by default",
    type=click.Choice(["True", "False"]),
    default=True
)
@click.option(
    '--common-server', '-c',
    help="Add an import for CommonServerPython."
         "If not specified will import unless this is CommonServerPython",
    type=click.Choice(["True", "False"]),
    default='True'
)
@pass_config
def extract(config, **kwargs):
    extractor = Extractor(configuration=config.configuration, **kwargs)
    return extractor.extract_to_package_format()


@main.command(name="extract-code",
              short_help="Extract code from a Demisto integration or script yaml file.")
@click.help_option(
    '-h', '--help'
)
@click.option(
    '--infile', '-i',
    help='The yml file to extract from',
    required=True
)
@click.option(
    '--outfile', '-o',
    required=True,
    help="The output file to write the code to"
)
@click.option(
    '--yml-type', '-y',
    help="Yaml type. If not specified will try to determine type based upon path.",
    type=click.Choice([SCRIPT_PREFIX, INTEGRATION_PREFIX])
)
@click.option(
    '--demisto-mock', '-d',
    help="Add an import for demisto mock, true by default",
    type=click.Choice(["True", "False"]),
    default=True
)
@click.option(
    '--common-server', '-c',
    help="Add an import for CommonServerPython."
         "If not specified will import unless this is CommonServerPython",
    type=click.Choice(["True", "False"]),
    default='True'
)
@pass_config
def extract_code(config, **kwargs):
    extractor = Extractor(configuration=config.configuration, **kwargs)
    return extractor.extract_code(kwargs['outfile'])


@main.command(name="unify",
              short_help='Unify code, image, description and yml files to a single Demisto yml file.')
@click.option(
    "-i", "--indir", help="The path to the files to unify", required=True
)
@click.option(
    "-o", "--outdir", help="The output dir to write the unified yml to", required=True
)
def unify(**kwargs):
    unifier = Unifier(**kwargs)
    return unifier.merge_script_package_to_yml()


# TODO: add a configuration for conf.json and id_set.json
@main.command(name="validate",
              short_help='Validate your content files.')
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-j', '--conf-json', is_flag=True,
    default=False, help='Validate the conf.json file.')
@click.option(
    '-i', '--id-set', is_flag=True,
    default=False, help='Create the id_set.json file.')
@click.option(
    '-p', '--prev-ver', help='Previous branch or SHA1 commit to run checks against.')
@click.option(
    '-c', '--circle', type=click.Choice(["True", "False"]), default='False',
    help='Is CircleCi or not')
@click.option(
    'b', '--backward-comp', type=click.Choice(["True", "False"]), default='False',
    help='To check backward compatibility.')
@click.option(
    '-g', '--use-git', is_flag=True,
    default=False, help='Validate changes using git - this will check your branch changes and will run only on them.')
@pass_config
def validate(config, **kwargs):
    sys.path.append(config.configuration.env_dir)

    validator = FilesValidator(configuration=config.configuration,
                               is_backward_check=str2bool(kwargs['backward-comp']),
                               is_circle=str2bool(kwargs['circle']), prev_ver=kwargs['prev_ver'],
                               validate_conf_json=kwargs['conf_json'], use_git=kwargs['use_git'])
    return validator.run()


@main.command(name="create",
              short_help='Create content artifacts.')
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-a', '--artifacts_path', help='The path of the directory in which you want to save the created content artifacts')
@click.option(
    '-p', '--preserve_bundles', is_flag=True, default=False,
    help='Keep the bundles created in the process of making the content artifacts')
def create(**kwargs):
    content_creator = ContentCreator(**kwargs)
    return content_creator.run()


@main.command(name="secrets",
              short_help="Run Secrets validator to catch sensitive data before exposing your code to public repository."
                         " Attach path to whitelist to allow manual whitelists. Default file path to secrets is "
                         "'./Tests/secrets_white_list.json' ")
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-c', '--circle', type=click.Choice(["True", "False"]), default='False',
    help='Is CircleCi or not')
@click.option(
    '-wl', '--whitelist', default='./Tests/secrets_white_list.json',
    help='Full path to whitelist file, file name should be "secrets_white_list.json"')
@pass_config
def secrets(config, **kwargs):
    sys.path.append(config.configuration.env_dir)
    secrets = SecretsValidator(configuration=config.configuration, is_circle=str2bool(kwargs['circle']),
                               white_list_path=kwargs['whitelist'])
    return secrets.run()


@main.command(name="lint",
              short_help="Run lintings (flake8, mypy, pylint, bandit) and pytest. pylint and pytest will run within the"
                         "docker image of an integration/script. Meant to be used with integrations/scripts that use "
                         "the folder (package) structure. Will lookup up what docker image to use and will setup the "
                         "dev dependencies and file in the target folder. ")
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-d", "--dir", help="Specify directory of integration/script", required=True)
@click.option(
    "--no-pylint", is_flag=True, help="Do NOT run pylint linter")
@click.option(
    "--no-mypy", is_flag=True, help="Do NOT run mypy static type checking")
@click.option(
    "--no-flake8", is_flag=True, help="Do NOT run flake8 linter")
@click.option(
    "--no-bandit", is_flag=True, help="Do NOT run bandit linter")
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
@pass_config
def lint(config, dir, **kwargs):
    linter = LintManager(configuration=config.configuration, project_dir=dir, **kwargs)
    return linter.run_dev_packages()


@main.command(name="format",
              short_help="Run formatter on a given script/playbook/integration yml file. ")
@click.help_option(
    '-h', '--help'
)
@click.option(
    "-t", "--file-type", type=click.Choice(["integration", "script", "playbook"]),
    help="The type of yml file to be formatted.", required=True)
@click.option(
    "-s", "--source-file", help="The path of the script yml file", required=True)
@click.option(
    "-o", "--output-file-name", help="The path where the formatted file will be saved to")
def format(file_type, **kwargs):
    file_type_and_linked_class = {
        'integration': IntegrationYMLFormat,
        'script': ScriptYMLFormat,
        'playbook': PlaybookYMLFormat
    }
    if file_type in file_type_and_linked_class:
        format_object = file_type_and_linked_class[file_type](**kwargs)
        return format_object.format_file()

    return 1


@main.command(name="spell-check",
              short_help="Run spell check on a given yml/md file.")
@click.help_option(
    '-h', '--help'
)
@click.option(
    '-p', '--path', help="Specify path of yml/md file", required=True)
@click.option(
    '--known-words', help="A file path to a txt file with known words")
def spell_check(**kwargs):
    spell_checker = SpellCheck(**kwargs)
    spell_checker.run_spell_check()
    return 0


@main.resultcallback()
def exit_from_program(result=0, **kwargs):
    sys.exit(result)


def demisto_sdk_cli():
    main()


if __name__ == '__main__':
    sys.exit(main())
