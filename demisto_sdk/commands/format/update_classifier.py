from abc import ABC
from typing import Tuple

import click

from demisto_sdk.commands.common.constants import OLDEST_SUPPORTED_VERSION
from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class BaseClassifierJSONFormat(BaseUpdateJSON, ABC):
    def __init__(self,
                 input: str = '',
                 output: str = '',
                 path: str = '',
                 from_version: str = '',
                 no_validate: bool = False,
                 verbose: bool = False,
                 **kwargs):
        super().__init__(input=input, output=output, path=path, from_version=from_version, no_validate=no_validate,
                         verbose=verbose, **kwargs)

    def run_format(self) -> int:
        super().update_json()
        return SUCCESS_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the Classifier JSON updater."""
        format_res = self.run_format()
        return format_res, SKIP_RETURN_CODE


class OldClassifierJSONFormat(BaseClassifierJSONFormat):
    """OldClassifierJSONFormat class is designed to update old classifier (version lower than 6.0.0) JSON file
    according to Demisto's convention.

       Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the JSON to.
    """

    def run_format(self) -> int:
        try:
            click.secho(f'\n================= Updating file {self.source_file} =================', fg='bright_blue')
            super().run_format()
            self.set_toVersion()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE

        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE


class ClassifierJSONFormat(BaseClassifierJSONFormat):
    """ClassifierJSONFormat class is designed to update classifier (version 6.0.0 and greater) JSON file according
    to Demisto's convention.

       Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to."""

    def run_format(self) -> int:
        try:
            click.secho(f'\n================= Updating file {self.source_file} =================', fg='bright_blue')
            super().run_format()
            self.set_fromVersion(OLDEST_SUPPORTED_VERSION)
            self.set_description()
            self.set_keyTypeMap()
            self.set_transformer()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE

        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
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
