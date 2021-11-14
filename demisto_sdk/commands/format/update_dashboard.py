from typing import Tuple

import click

from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class DashboardJSONFormat(BaseUpdateJSON):
    """DashboardJSONFormat class is designed to update dashboard JSON file according to Demisto's convention.

       Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the JSON to.
    """

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
        try:
            click.secho(f'\n================= Updating file {self.source_file} =================', fg='bright_blue')
            super().update_json()
            self.default_description()
            self.update_id()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def default_description(self):
        if not self.data.get("description", ""):
            self.data["description"] = ""
        if not self.data.get("isPredefined", ""):
            self.data["isPredefined"] = True

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the Dashboard JSON updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()
