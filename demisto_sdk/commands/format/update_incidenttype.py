from demisto_sdk.commands.common.tools import print_color, LOG_COLORS
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON
from demisto_sdk.commands.common.hook_validations.incident_field import IncidentFieldValidator


class IncidentTypesJSONFormat(BaseUpdateJSON):
    """IncidentTypesJSONFormat class is designed to update incident fields JSON file according to Demisto's convention.

        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file_name (str): the desired file name to save the updated version of the YML to.
            json_data (Dict): YML file data arranged in a Dict.
    """

    def __init__(self, source_file='', output_file_name=''):
        super().__init__(source_file, output_file_name)

    def format_file(self):
        """Manager function for the integration YML updater."""

        print_color(F'========Starting updates for incident field: {self.source_file}=======', LOG_COLORS.YELLOW)

        super().update_json()

        print_color(F'========Finished updates for incident field: {self.output_file_name}=======',
                    LOG_COLORS.YELLOW)

        return self.initiate_file_validator(IncidentFieldValidator, 'incident_field')
