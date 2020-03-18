from demisto_sdk.commands.common.tools import print_color, LOG_COLORS
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON
from demisto_sdk.commands.common.hook_validations.layout import LayoutValidator


DEFAULT_JSON_VERSION = -1


class LayoutJSONFormat(BaseUpdateJSON):
    """LayoutJSONFormat class is designed to update layout JSON file according to Demisto's convention.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
            json_data (Dict): YML file data arranged in a Dict.
    """

    def __init__(self, input='', output='', old_file='', path='', from_version=''):
        super().__init__(input, output, old_file, path, from_version)

    def set_version_to_default(self):
        """Replaces the version of the YML to default."""
        print(F'Setting JSON version to default: {self.DEFAULT_JSON_VERSION}')
        self.json_data['layout']['version'] = self.DEFAULT_JSON_VERSION  # ?  ?????

    def format_file(self):
        """Manager function for the integration YML updater."""

        print_color(F'========Starting updates for incident field: {self.source_file}=======', LOG_COLORS.YELLOW)

        self.set_version_to_default()
        self.remove_unnecessary_keys()
        self.set_fromVersion(from_version=self.from_version)
        super().save_json_to_destination_file()

        print_color(F'========Finished updates for incident field: {self.output_file_name}=======',
                    LOG_COLORS.YELLOW)

        return self.initiate_file_validator(LayoutValidator)
