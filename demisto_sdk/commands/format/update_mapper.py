import logging
from typing import Tuple

import click

from demisto_sdk.commands.common.constants import LAYOUT_AND_MAPPER_BUILT_IN_FIELDS
from demisto_sdk.commands.common.tools import (
    get_all_incident_and_indicator_fields_from_id_set,
    get_invalid_incident_fields_from_mapper,
)
from demisto_sdk.commands.common.update_id_set import BUILT_IN_FIELDS
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON

logger = logging.getLogger("demisto-sdk")


class MapperJSONFormat(BaseUpdateJSON):
    """MapperJSONFormat class is designed to update mapper JSON file according to Demisto's convention.

    Attributes:
         input (str): the path to the file we are updating at the moment.
         output (str): the desired file name to save the updated version of the YML to.
    """

    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
        from_version: str = "",
        no_validate: bool = False,
        verbose: bool = False,
        **kwargs,
    ):
        super().__init__(
            input=input,
            output=output,
            path=path,
            from_version=from_version,
            no_validate=no_validate,
            verbose=verbose,
            **kwargs,
        )

    def run_format(self) -> int:
        try:
            click.secho(
                f"\n================= Updating file {self.source_file} =================",
                fg="bright_blue",
            )
            super().update_json()
            self.set_description()
            self.set_mapping()
            self.update_id()
            self.remove_non_existent_fields()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE

        except Exception as err:
            if self.verbose:
                click.secho(
                    f"\nFailed to update file {self.source_file}. Error: {err}",
                    fg="red",
                )
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the mapper JSON updater."""
        format_res = self.run_format()
        return format_res, SKIP_RETURN_CODE

    def set_mapping(self):
        """
        mapping is a required field for mappers.
        If the key does not exist in the json file, a field will be set with {} value

        """
        if not self.data.get("mapping"):
            self.data["mapping"] = {}

    def remove_non_existent_fields(self):
        """
        Remove non-existent fields from a mapper.
        """
        if not self.id_set_file:
            logger.warning(
                f"Skipping formatting of non-existent-fields for {self.source_file} as id_set_path argument is missing"
            )
            return

        content_fields = (
            get_all_incident_and_indicator_fields_from_id_set(
                self.id_set_file, "mapper"
            )
            + [field.lower() for field in BUILT_IN_FIELDS]
            + LAYOUT_AND_MAPPER_BUILT_IN_FIELDS
        )

        mapper = self.data.get("mapping", {})
        mapping_type = self.data.get("type", {})

        for mapping_name in mapper.values():
            internal_mapping_fields = mapping_name.get("internalMapping", {})
            mapping_name["internalMapping"] = {
                inc_name: inc_info
                for inc_name, inc_info in internal_mapping_fields.items()
                if inc_name
                not in get_invalid_incident_fields_from_mapper(
                    mapper_incident_fields=internal_mapping_fields,
                    mapping_type=mapping_type,
                    content_fields=content_fields,
                )
            }
