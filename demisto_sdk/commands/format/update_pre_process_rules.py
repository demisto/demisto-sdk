import os
from typing import Tuple

import click
import traceback

from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)

from demisto_sdk.commands.common.hook_validations.pre_process_rule import PreProcessRuleValidator
from demisto_sdk.commands.format.format_constants import (SKIP_RETURN_CODE, SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON

PRE_PROCESS_RULES_PREFIX = 'preprocessrule-'

FROM_VERSION_PRE_PROCESS_RULES = '6.5.0'

class PreProcessRulesBaseFormat(BaseUpdateJSON):

    def __init__(self,
                 input: str = '',
                 output: str = '',
                 path: str = 'pre-process-rules',
                 from_version: str = '',
                 no_validate: bool = False,
                 verbose: bool = False,
                 **kwargs):
        super().__init__(input=input, output=output, path=path, from_version=from_version, no_validate=no_validate,
                         verbose=verbose, **kwargs)

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the PreProcessRules JSON updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator(PreProcessRuleValidator)

    def run_format(self) -> int:
        try:
            click.secho(f'\n======= Updating file: {self.source_file} =======', fg='white')
            self.set_version_to_default()
            self.remove_unnecessary_keys()

            self.pre_process_rules__set_output_path()
            self.set_from_server_version_to_default()

            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            print(''.join(traceback.format_exception(etype=type(err), value=err, tb=err.__traceback__)))
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def set_from_server_version_to_default(self, location=None):
        """Replaces the fromServerVersion of the YML to default."""
        if self.verbose:
            click.echo(f'Trying to set JSON fromServerVersion to default: {FROM_VERSION_PRE_PROCESS_RULES}')
        if location and not location['fromServerVersion']:
            location['fromServerVersion'] = FROM_VERSION_PRE_PROCESS_RULES
        else:
            if not self.data['fromServerVersion']:
                self.data['fromServerVersion'] = FROM_VERSION_PRE_PROCESS_RULES

    def pre_process_rules__set_output_path(self):
        output_basename = os.path.basename(self.output_file)
        if not output_basename.startswith(PRE_PROCESS_RULES_PREFIX):
            new_output_basename = PRE_PROCESS_RULES_PREFIX + output_basename
            new_output_path = self.output_file.replace(output_basename, new_output_basename)

            # rename file if source and output are the same
            if self.output_file == self.source_file:
                os.rename(self.source_file, new_output_path)
                self.source_file = new_output_path

            self.output_file = new_output_path
