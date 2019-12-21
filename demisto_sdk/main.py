import sys
import click
from pkg_resources import get_distribution

from demisto_sdk.core import DemistoSDK
from demisto_sdk.common.tools import str2bool
from demisto_sdk.yaml_tools.unifier import Unifier
from demisto_sdk.yaml_tools.extractor import Extractor
from demisto_sdk.common.configuration import Configuration
from demisto_sdk.validation.file_validator import FilesValidator
from demisto_sdk.common.constants import SCRIPT_PREFIX, INTEGRATION_PREFIX


pass_config = click.make_pass_decorator(DemistoSDK, ensure=True)


@click.group(invoke_without_command=True)
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
        config.env_dir = env_dir


@main.command(name="extract",
              help="Extract code, image and description files "
                   "from a Demisto integration or script yaml file")
@click.option(
    '--infile', '-i',
    help='The yml file to extract from',
    required=True
)
@click.option(
    '--outfile', '-o',
    required=True,
    help="The output file or dir (if doing migrate) to write the code to"
)
@click.option(
    '--migrate', '-m',
    help="Migrate an integration to package format."
         " Pass to -o option a directory in this case.",
    is_flag=True,
    default=False
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
    default='False'
)
@pass_config
def extract(config, **kwargs):
    print(config.configuration.env_dir)
    extractor = Extractor(configuration=config.configuration, **kwargs)
    return extractor.run()


@main.command(name="unify",
              help='Unify code, image and description files to a single Demisto yaml file')
@click.option(
    "-i", "--indir", help="The path to the files to unify", required=True
)
@click.option(
    "-o", "--outdir", help="The output dir to write the unified yml to", required=True
)
def unify(**kwargs):
    unifier = Unifier(**kwargs)
    return unifier.merge_script_package_to_yml()


@main.command(name="validate",
              help='Validate your content files')
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
    '-b', '--backward-comp', type=click.Choice(["True", "False"]), default='True',
    help='To check backward compatibility.')
@click.option(
    '-g', '--use-git', is_flag=True,
    default=False, help='Validate changes using git.')
@pass_config
def validate(config, **kwargs):
    sys.path.append(config.configuration.env_dir)

    validator = FilesValidator(configuration=config.configuration, is_backward_check=str2bool(kwargs['backward_comp']),
                               is_circle=str2bool(kwargs['circle']), prev_ver=kwargs['prev_ver'],
                               validate_conf_json=kwargs['conf_json'], use_git=kwargs['use_git'])
    return validator.run()


if __name__ == '__main__':
    sys.exit(main())
