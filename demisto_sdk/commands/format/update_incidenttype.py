from typing import Tuple

import click

from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class IncidentTypesJSONFormat(BaseUpdateJSON):
    """IncidentTypesJSONFormat class is designed to update incident types JSON file according to Demisto's convention.


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
            self.format_auto_extract_mode()
            self.set_default_values_as_needed()
            self.update_id()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def format_auto_extract_mode(self):
        """
         When formatting incident types with Auto-Extract rules and without mode field,
         the function will add the user selected mode.
        """

        auto_extract_settings = self.data.get('extractSettings', {})
        if auto_extract_settings:
            auto_extract_mode = auto_extract_settings.get('mode')
            if not auto_extract_mode or auto_extract_mode not in ['All', 'Specific']:
                user_input = ''
                while user_input not in ['All', 'Specific']:
                    user_input = click.prompt(
                        ' The `mode` field under `extractSettings` should be one of the following: \n'
                        '- "All" - To extract all indicator types regardless of auto-extraction settings. \n'
                        '- "Specific" - To extract only the specific indicator types set in the auto-extraction '
                        'settings.')

                if user_input == 'All' and auto_extract_settings['fieldCliNameToExtractSettings']:
                    click.secho('Cannot set mode to "All" since there are specific types under the '
                                'fieldCliNameToExtractSettings, '
                                'If you want the mode to be "All" you should delete them manually and run this '
                                'command again.', fg='yellow')
                    return
                if user_input == 'Specific' and not self.data['extractSettings']['fieldCliNameToExtractSettings']:
                    click.secho('Please notice that mode was set to "Specific" but there are no specific types under '
                                'fieldCliNameToExtractSettings', fg='yellow')
                self.data['extractSettings']['mode'] = user_input

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the incident type JSON updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()
