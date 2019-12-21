import sys
import click
from pkg_resources import get_distribution

from demisto_sdk.core import DemistoSDK
from demisto_sdk.common.configuration import Configuration
from demisto_sdk.yaml_tools.extractor import Extractor
from demisto_sdk.yaml_tools.unifier import Unifier
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
    default=False
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


if __name__ == '__main__':
    sys.exit(main())
