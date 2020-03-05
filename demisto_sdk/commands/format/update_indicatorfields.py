from demisto_sdk.commands.common.tools import print_color, LOG_COLORS
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON
from demisto_sdk.commands.common.hook_validations.incident_field import IncidentFieldValidator

ARGUMENTS_DEFAULT_VALUES = {
    'content': 'true',
    'system': 'false',
    'required': 'false',
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


class IncidentFieldJSONFormat(BaseUpdateJSON):
    """IncidentFieldJSONFormat class is designed to update incident fields JSON file according to Demisto's convention.

        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file_name (str): the desired file name to save the updated version of the YML to.
            json_data (Dict): YML file data arranged in a Dict.
    """

    def __init__(self, source_file='', output_file_name=''):
        super().__init__(source_file, output_file_name)

    def set_default_values_as_needed(self):
        """Sets basic arguments of reputation commands to be default, isArray and required."""
        print(F'Updating required default values')

        for field in ARGUMENTS_DEFAULT_VALUES:
            self.json_data[field] = ARGUMENTS_DEFAULT_VALUES[field]

    def remove_unnecessary_keys(self):
        for key in ARGUMENTS_TO_REMOVE:
            self.json_data.pop(key, None)

    def format_file(self):
        """Manager function for the integration YML updater."""
        super().update_json()

        print_color(F'========Starting updates for incident field: {self.source_file}=======', LOG_COLORS.YELLOW)

        self.set_default_values_as_needed()

        print_color(F'========Finished updates for incident field: {self.output_file_name}=======',
                    LOG_COLORS.YELLOW)

        return self.initiate_file_validator(IncidentFieldValidator, 'incident_field')
