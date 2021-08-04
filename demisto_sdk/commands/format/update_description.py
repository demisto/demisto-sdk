import re
from typing import Tuple

import click

from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic import BaseUpdate

CONTRIBUTOR_DETAILED_DESC = 'Contributed Integration'


class DescriptionFormat(BaseUpdate):
    """DescriptionFormat class is designed to update integration description file according to Demisto's convention.

        Attributes:
            input (str): the path to the file we are updating at the moment.
    """

    def __init__(self,
                 input: str = '',
                 output: str = '',
                 path: str = '',
                 from_version: str = '',
                 no_validate: bool = False,
                 verbose: bool = False,
                 update_docker: bool = False,
                 **kwargs):
        super().__init__(input, output, path, from_version, no_validate, verbose=verbose, **kwargs)

    def remove_community_partner_details(self):
        """update description file to not contain community/partner details"""

        with open(self.source_file, 'r') as f:
            description_content = f.read()
        formatted_description = re.sub('###.*Contributed Integration[\\S\n ]+?[*]{3}[\n]*', "", description_content)
        formatted_description = formatted_description.rstrip("\n")

        with open(self.source_file, 'w') as f:
            f.write(formatted_description)
        f.close()

    def run_format(self) -> int:
        try:
            click.secho(f'\n================= Updating file {self.source_file} ================= ', fg='bright_blue')
            self.remove_community_partner_details()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration description updater."""

        format = self.run_format()
        if format:
            return format, SKIP_RETURN_CODE
        else:
            return format, self.initiate_file_validator()
