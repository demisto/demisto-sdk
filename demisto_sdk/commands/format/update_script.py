from demisto_sdk.commands.common.tools import print_color, LOG_COLORS
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML
from demisto_sdk.commands.common.hook_validations.script import ScriptValidator


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
        """Manager function for the script YML updater."""
        super().update_yml()

        print_color(F'========Starting updates for script: {self.source_file}=======', LOG_COLORS.YELLOW)

        self.save_yml_to_destination_file()

        print_color(F'========Finished updates for script: {self.output_file_name}=======', LOG_COLORS.YELLOW)

        return self.initiate_file_validator(ScriptValidator, 'script')
