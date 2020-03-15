from demisto_sdk.commands.common.tools import print_color, LOG_COLORS
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON
from demisto_sdk.commands.common.hook_validations.incident_field import IncidentFieldValidator

ARGUMENTS_DEFAULT_VALUES = {
    'content': True,
    'system': False,
    'required': False,
}

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


class IndicatorFieldJSONFormat(BaseUpdateJSON):
    """IndicatorFieldJSONFormat class is designed to update incident fields JSON file according to Demisto's convention.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
            json_data (Dict): YML file data arranged in a Dict.
    """

    def __init__(self, input='', output='', old_file=''):
        super().__init__(input, output, old_file)

    def format_file(self):
        """Manager function for the integration YML updater."""
        super().update_json()

        print_color(F'========Starting updates for indicator field: {self.source_file}=======', LOG_COLORS.YELLOW)

        super().set_default_values_as_needed(ARGUMENTS_DEFAULT_VALUES)
        super().remove_unnecessary_keys(ARGUMENTS_TO_REMOVE)
        super().set_fromVersion()
        super().save_json_to_destination_file()

        print_color(F'========Finished updates for indicator field: {self.output_file_name}=======',
                    LOG_COLORS.YELLOW)

        return self.initiate_file_validator(IncidentFieldValidator, 'incidentfield')
