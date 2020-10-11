from typing import Tuple

import click
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON
from demisto_sdk.tests.constants_test import CONNECTION_SCHEMA_PATH


class ConnectionJSONFormat(BaseUpdateJSON):
    """ConnectionJSONFormat class is designed to update connections JSON file according to Demisto's convention.

       Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the JSON to.
    """

    def __init__(self,
                 input: str = '',
                 output: str = '',
                 path: str = CONNECTION_SCHEMA_PATH,
                 from_version: str = '',
                 no_validate: bool = False,
                 verbose: bool = False,
                 **kwargs):
        super().__init__(input=input,
                         output=output,
                         path=path,
                         from_version=from_version,
                         no_validate=no_validate,
                         verbose=verbose)

    def run_format(self) -> int:
        try:
            click.secho(f'\n======= Updating file: {self.source_file} =======', fg='white')
            self.remove_unnecessary_keys()
            self.set_fromVersion(from_version=self.from_version)
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception:
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the indicator type JSON updater."""
        format = self.run_format()
        if format:
            return format, SKIP_RETURN_CODE
        else:
            return format, self.initiate_file_validator(ContentEntityValidator)
