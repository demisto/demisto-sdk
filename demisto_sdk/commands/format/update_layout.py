from typing import Tuple

import yaml
from demisto_sdk.commands.common.hook_validations.layout import LayoutValidator
from demisto_sdk.commands.common.tools import LOG_COLORS, print_color
from demisto_sdk.commands.format.format_constants import (
    DEFAULT_VERSION, ERROR_RETURN_CODE, NEW_FILE_DEFAULT_5_FROMVERSION,
    SKIP_RETURN_CODE, SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class LayoutJSONFormat(BaseUpdateJSON):
    """LayoutJSONFormat class is designed to update layout JSON file according to Demisto's convention.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
    """

    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = '', no_validate: bool = False):
        super().__init__(input, output, path, from_version, no_validate)

    def remove_unnecessary_keys(self):
        print('Removing Unnecessary fields from file')
        arguments_to_remove = self.arguments_to_remove()
        for key in arguments_to_remove:
            print(F'Removing Unnecessary fields {key} from file')
            self.data['layout'].pop(key, None)

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

    def set_layout_key(self):
        if "layout" not in self.data.keys():
            kind = self.data['kind']
            id = self.data['id']
            self.data = {
                "typeId": id,
                "version": DEFAULT_VERSION,
                "TypeName": id,
                "kind": kind,
                "fromVersion": NEW_FILE_DEFAULT_5_FROMVERSION,
                "layout": self.data
            }

    def run_format(self) -> int:
        try:
            print_color(F'=======Starting updates for file: {self.source_file}=======', LOG_COLORS.YELLOW)
            self.set_layout_key()
            # version is both in layout key and in base dict
            self.set_version_to_default()
            self.set_version_to_default(self.data['layout'])
            self.remove_unnecessary_keys()
            self.set_fromVersion(from_version=self.from_version)
            super().save_json_to_destination_file()

            print_color(F'=======Finished updates for files: {self.output_file}=======', LOG_COLORS.YELLOW)
            return SUCCESS_RETURN_CODE
        except Exception:
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration YML updater."""
        format = self.run_format()
        if format:
            return format, SKIP_RETURN_CODE
        else:
            return format, self.initiate_file_validator(LayoutValidator)
