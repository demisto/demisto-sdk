from typing import Tuple

import click

from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class ConnectionJSONFormat(BaseUpdateJSON):
    """ConnectionJSONFormat class is designed to update connections JSON file according to Demisto's convention.

        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file (str): the desired file name to save the updated version of the YML to.
            relative_content_path (str): Relative content path of output path.
            old_file (dict): Data of old file from content repo, if exist.
            schema_path (str): Schema path of file.
            from_version (str): Value of Wanted fromVersion key in file.
            data (dict): Dictionary of loaded file.
            file_type (str): Whether the file is yml or json.
            from_version_key (str): The fromVersion key in file, different between yml and json files.
            verbose (bool): Whether to print a verbose log
    """

    def __init__(self,
                 input: str = '',
                 output: str = '',
                 path: str = '',
                 from_version: str = '',
                 no_validate: bool = False,
                 verbose: bool = False,
                 **kwargs):
        super().__init__(input=input,
                         output=output,
                         path=path,
                         from_version=from_version,
                         no_validate=no_validate,
                         verbose=verbose, **kwargs)

    def run_format(self) -> int:
        try:
            click.secho(f'\n================= Updating file {self.source_file} =================', fg='bright_blue')
            self.remove_unnecessary_keys()
            self.set_fromVersion(from_version=self.from_version)
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the indicator type JSON updater."""
        format_ = self.run_format()
        if format_:
            return format_, SKIP_RETURN_CODE
        else:
            return format_, self.initiate_file_validator()
