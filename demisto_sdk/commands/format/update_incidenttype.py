from typing import Dict, Optional, Tuple

import click
from demisto_sdk.commands.common.hook_validations.incident_type import \
    IncidentTypeValidator
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
                         verbose=verbose)

    def run_format(self) -> Tuple[int, Optional[Dict]]:
        try:
            click.secho(f'\n======= Updating file: {self.source_file} =======', fg='white')
            super().update_json()
            self.set_default_values_as_needed()
            content_entity_ids_to_update = self.update_id()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE, content_entity_ids_to_update
        except Exception:
            return ERROR_RETURN_CODE, None

    def format_file(self) -> Tuple[int, int, Optional[Dict[str, str]]]:
        """Manager function for the incident type JSON updater."""
        format_res, content_entity_ids_to_update = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE, content_entity_ids_to_update
        else:
            return format_res, self.initiate_file_validator(IncidentTypeValidator), content_entity_ids_to_update
