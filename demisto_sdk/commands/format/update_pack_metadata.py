import traceback
from pathlib import Path
from typing import Tuple

import click

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class PackMetaDataFormat(BaseUpdateJSON):

    def __init__(self,
                 input: str = '',
                 output: str = '',
                 no_validate: bool = False,
                 verbose: bool = False,
                 **kwargs):
        super().__init__(input=input, output=output, no_validate=no_validate,
                         verbose=verbose, **kwargs)

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the pack_metadata JSON updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

    def run_format(self) -> int:
        try:
            click.secho(f'\n======= Updating file: {self.source_file} =======', fg='white')
            self.update_marketplace()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            print(''.join(traceback.format_exception(type(err), value=err, tb=err.__traceback__)))
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def update_marketplace(self):

        path_pack = str(Path(self.source_file).parent)
        marketplaces = self.data.get('marketplaces')
        if not marketplaces:
            if tools.does_pack_belong_siam(path_pack):
                self.data['marketplaces'] = ['xsoar', 'marketplacev2']
            else:
                self.data['marketplaces'] = ['xsoar']

        elif 'marketplacev2' not in marketplaces and tools.does_pack_belong_siam(path_pack):
            self.data['marketplaces'] = ['xsoar', 'marketplacev2']
