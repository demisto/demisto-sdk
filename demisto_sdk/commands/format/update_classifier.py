from abc import ABC
from typing import Tuple

from demisto_sdk.commands.common.tools import LOG_COLORS, print_color
from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE,
                                                          VERSION_6_0_0)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class BaseClassifierJSONFormat(BaseUpdateJSON, ABC):
    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = '',
                 no_validate: bool = False):
        super().__init__(input, output, path, from_version, no_validate)

    def run_format(self):
        super().update_json()
        self.save_json_to_destination_file()

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration YML updater."""
        format = self.run_format()
        if format:
            return format, SKIP_RETURN_CODE
        else:
            return format, SKIP_RETURN_CODE


class OldClassifierJSONFormat(BaseClassifierJSONFormat):
    """OldClassifierJSONFormat class is designed to update old classifier (version lower than 6.0.0) JSON file
    according to Demisto's convention.

       Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the JSON to.
    """

    def run_format(self) -> int:
        try:
            print_color(F'\n=======Starting updates for file: {self.source_file}=======', LOG_COLORS.WHITE)
            self.set_toVersion()
            super().run_format()
            print_color(F'=======Finished updates for files: {self.output_file}=======\n', LOG_COLORS.WHITE)
            return SUCCESS_RETURN_CODE

        except Exception:
            return ERROR_RETURN_CODE


class ClassifierJSONFormat(BaseClassifierJSONFormat):
    """ClassifierJSONFormat class is designed to update classifier (version 6.0.0 and greater) JSON file according
    to Demisto's convention.

       Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to."""

    def run_format(self) -> int:
        try:
            print_color(F'\n=======Starting updates for file: {self.source_file}=======', LOG_COLORS.WHITE)
            self.set_fromVersion(VERSION_6_0_0)
            self.set_description()
            self.set_keyTypeMap()
            self.set_transformer()
            super().run_format()
            print_color(F'=======Finished updates for files: {self.output_file}=======\n', LOG_COLORS.WHITE)
            return SUCCESS_RETURN_CODE

        except Exception:
            return ERROR_RETURN_CODE

    def set_keyTypeMap(self):
        """
        keyTypeMap is a required field for new classifiers.
        If the key does not exist in the json file, a field will be set with {} value

        """
        if not self.data.get('keyTypeMap'):
            self.data['keyTypeMap'] = {}

    def set_transformer(self):
        """
        transformer is a required field for new classifiers.
        If the key does not exist in the json file, a field will be set with {} value

        """
        if not self.data.get('transformer'):
            self.data['transformer'] = {}
