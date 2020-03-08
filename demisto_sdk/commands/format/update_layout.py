from demisto_sdk.commands.common.tools import print_color, LOG_COLORS
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON
from demisto_sdk.commands.common.hook_validations.layout import LayoutValidator


ARGUMENTS_TO_REMOVE = ['sortValues',
                       'vcShouldIgnore',
                       'commitMessage',
                       'shouldCommit',
                       'prevName',
                       'validatedError',
                       'shouldPublish',
                       'shouldPush',
                       'modified',
                       'prevDetails',
                       'prevKind',
                       'prevTypeId',
                       'prevType']


class LayoutJSONFormat(BaseUpdateJSON):
    """LayoutJSONFormat class is designed to update incident fields JSON file according to Demisto's convention.

        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file_name (str): the desired file name to save the updated version of the YML to.
            json_data (Dict): YML file data arranged in a Dict.
    """

    def __init__(self, source_file='', output_file_name='', old_file=''):
        super().__init__(source_file, output_file_name, old_file)

    def format_file(self):
        """Manager function for the integration YML updater."""
        super().update_json()

        print_color(F'========Starting updates for incident field: {self.source_file}=======', LOG_COLORS.YELLOW)

        super().remove_unnecessary_keys(ARGUMENTS_TO_REMOVE)
        super().set_fromVersion()
        super().save_json_to_destination_file()

        print_color(F'========Finished updates for incident field: {self.output_file_name}=======',
                    LOG_COLORS.YELLOW)

        return self.initiate_file_validator(LayoutValidator, 'layout')
