import sys
import click
from pkg_resources import get_distribution

from demisto_sdk.common.configuration import Configuration
from demisto_sdk.yaml_tools.extractor import Extractor
from demisto_sdk.common.constants import SCRIPT_PREFIX, INTEGRATION_PREFIX


class DemistoSDK():
    def __init__(self):
        self.configuration = None


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
    '--type', '-t',
    help="Yaml type. If not specified will try to determine type based upon path.",
    type=click.Choice([SCRIPT_PREFIX, INTEGRATION_PREFIX])
)
@click.option(
    '--demistomock', '-d',
    help="Add an import for demisto mock, true by default",
    type=click.Choice([True, False]),
    default=True
)
@click.option(
    '--commonserver', '-c',
    help="Add an import for CommonServerPython."
         "If not specified will import unless this is CommonServerPython",
    type=click.Choice([True, False]),
    default=False
)
@pass_config
def extract(config, **kwargs):
    print(config.configuration.env_dir)
    # extractor = Extractor(configuration=Configuration(), **kwargs)
    # return extractor.execute()

# def m(migrate, outfile, infile, type, commonserver, demistomock):
#     print(migrate)

@main.command(name="something")
@click.argument('location')
@click.option(
    '--sdf', '-s',
    help='your API key for the OpenWeatherMap API',
)
@click.option(
    '--fuck', '-f',
    help='your API key for the OpenWeatherMap API',
)
def kak(location, api_key):
    print("Asdfsf")


if __name__ == '__main__':
    sys.exit(main())
