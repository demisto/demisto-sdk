from demisto_sdk.commands.common.tools import print_color, LOG_COLORS
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON
from demisto_sdk.commands.common.hook_validations.layout import LayoutValidator
import yaml
DEFAULT_JSON_VERSION = -1


class LayoutJSONFormat(BaseUpdateJSON):
    """LayoutJSONFormat class is designed to update layout JSON file according to Demisto's convention.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
    """

    def __init__(self, input='', output='', path='', from_version=''):
        super().__init__(input, output, path, from_version)

    def set_version_to_default(self):
        """Replaces the version of the YML to default."""
        print(F'Setting JSON version to default: {DEFAULT_JSON_VERSION}')
        self.data['layout']['version'] = DEFAULT_JSON_VERSION  # ?  ?????

    def remove_unnecessary_keys(self):
        print(F'Removing Unnecessary fields from file')
        for key in self.arguments_to_remove:
            print(F'Removing Unnecessary fields {key} from file')
            self.data['layout'].pop(key, None)

    def format_file(self):
        """Manager function for the integration YML updater."""

        print_color(F'========Starting updates for incident field: {self.source_file}=======', LOG_COLORS.YELLOW)

        self.set_version_to_default()
        self.remove_unnecessary_keys()
        self.set_fromVersion(from_version=self.from_version)
        super().save_json_to_destination_file()

        print_color(F'========Finished updates for incident field: {self.output_file}=======',
                    LOG_COLORS.YELLOW)

        return self.initiate_file_validator(LayoutValidator)

    def arguments_to_remove(self):
        arguments_to_remove = []
        with open(self.schema_path, 'r') as file_obj:
            a = yaml.safe_load(file_obj)
        out_schema_fields = a.get('mapping').keys()
        out_file_fields = self.data.keys()
        for field in out_file_fields:
            if field not in out_schema_fields:
                arguments_to_remove.append(field)
        out_schema_fields = a.get('mapping').get('layout').get('mapping').keys()
        out_file_fields = self.data['layout'].keys()
        for field in out_file_fields:
            if field not in out_schema_fields:
                arguments_to_remove.append(field)
        return arguments_to_remove
