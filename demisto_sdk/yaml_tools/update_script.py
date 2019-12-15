from argparse import ArgumentDefaultsHelpFormatter

from demisto_sdk.yaml_tools.update_generic_yml import BaseUpdateYML


class ScriptYMLFormat(BaseUpdateYML):
    """ScriptYMLFormat class is designed to update script YML file according to Demisto's convention.

        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file_name (str): the desired file name to save the updated version of the YML to.
            yml_data (Dict): YML file data arranged in a Dict.
            id_and_version_location (Dict): the object in the yml_data that holds the is and version values.
    """
    def __init__(self, source_file='', output_file_name=''):
        super().__init__(source_file, output_file_name)

    @staticmethod
    def add_sub_parser(subparsers):
        description = """Run formatter on a given playbook yml file. """
        parser = subparsers.add_parser('format', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-p", "--path", help="Specify path of playbook yml file", required=True)
        parser.add_argument("-o", "--output-file", help="Specify path where the formatted file will be saved to")
