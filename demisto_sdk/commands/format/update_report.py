from typing import Tuple

import click

from demisto_sdk.commands.common.tools import (LOG_COLORS, print_color,
                                               print_error)
from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class ReportJSONFormat(BaseUpdateJSON):
    """ReportJSONFormat class is designed to update report JSON file according to Demisto's convention.

       Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
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
            self.update_json()
            self.set_description()
            self.set_recipients()
            self.set_type()
            self.set_orientation()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE

        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration YML updater."""
        format = self.run_format()
        return format, SKIP_RETURN_CODE

    def set_type(self):
        """
        type is a required field for reports which is
        limited for the following values:
        ['pdf', 'csv', 'docx']
        """
        if not self.data.get('type'):
            click.secho('No type is specified for this report, would you like me to update for you? [Y/n]',
                        fg='red')
            user_answer = input()
            # Checks if the user input is no
            if user_answer in ['n', 'N', 'No', 'no']:
                print_error('Moving forward without updating type field')
                return

            print_color('Please specify the desired type: pdf | csv | docx', LOG_COLORS.YELLOW)
            user_desired_type = input()
            if user_desired_type.lower() in ('pdf', 'csv', 'docx'):
                self.data['type'] = user_desired_type.lower()
            else:
                print_error('type is not valid')

    def set_orientation(self):
        """
        orientation is a required field for reports which is
        limited for the following values:
        ['landscape', 'portrait', '']
        """
        if not self.data.get('orientation'):
            click.secho('No orientation is specified for this report, would you like me to update for you? [Y/n]',
                        fg='red')
            user_answer = input()
            # Checks if the user input is no
            if user_answer in ['n', 'N', 'No', 'no']:
                print_error('Moving forward without updating orientation field')
                return

            click.secho('Please specify the desired orientation: landscape | portrait ', fg='yellow')
            user_desired_orientation = input()
            if user_desired_orientation.lower() in ('landscape', 'portrait'):
                self.data['orientation'] = user_desired_orientation.lower()
            else:
                self.data['orientation'] = ''

    def set_recipients(self):
        """
        recipients is a required field for reports that is
        If the key does not exist in the json file, a field will be set with [] value

        """
        if not self.data.get('recipients'):
            self.data['recipients'] = []
