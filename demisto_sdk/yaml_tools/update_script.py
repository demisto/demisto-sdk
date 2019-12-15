from argparse import ArgumentDefaultsHelpFormatter

# from demisto_sdk.common.tools import print_color, LOG_COLORS
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

    def format_file(self):
        """Manager function for the script YML updater.
        """
        super().update_yml()

        # when new format function will be added, this would be relevant.
        # print_color(F'========Starting specific updates for script: {self.source_file}=======', LOG_COLORS.YELLOW)
        # print_color(F'========Finished generic updates for script: {self.output_file_name}=======', LOG_COLORS.YELLOW)

    @staticmethod
    def add_sub_parser(subparsers):
        description = """Run formatter on a given script yml file. """
        parser = subparsers.add_parser('format', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-t", "--type", help="Specify the type of yml file to be formatted.", required=True)
        parser.add_argument("-p", "--path", help="Specify path of playbook yml file", required=True)
        parser.add_argument("-o", "--output-file", help="Specify path where the formatted file will be saved to")
