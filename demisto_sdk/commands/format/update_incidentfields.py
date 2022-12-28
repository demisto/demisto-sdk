from typing import List, Tuple

import click

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import (
    get_dict_from_file,
    get_item_marketplaces,
    open_id_set_file,
)
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON

json = JSON_Handler()


class IncidentFieldJSONFormat(BaseUpdateJSON):
    """IncidentFieldJSONFormat class is designed to update incident fields JSON file according to Demisto's convention.

    Attributes:
        input (str): the path to the file we are updating at the moment.
        output (str): the desired file name to save the updated version of the JSON to.
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
        self.id_set_path = kwargs.get("id_set_path")

    def run_format(self) -> int:
        try:
            click.secho(
                f"\n================= Updating file {self.source_file} =================",
                fg="bright_blue",
            )
            super().update_json()
            self.format_marketplaces_field_of_aliases()
            self.set_default_values_as_needed()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            if self.verbose:
                click.secho(
                    f"\nFailed to update file {self.source_file}. Error: {err}",
                    fg="red",
                )
            return ERROR_RETURN_CODE

    def format_marketplaces_field_of_aliases(self):
        """
        When formatting incident field with aliases,
        the function will update the marketplaces in the fields mapped by the aliases to be XSOAR marketplace only.
        """

        if not self.id_set_path:
            click.secho(
                'Skipping "Aliases" formatting as id_set_path argument is missing',
                fg="yellow",
            )

        aliases = self.data.get("Aliases", {})
        if aliases:
            for (
                alias_field,
                alias_field_file_path,
            ) in self._get_incident_fields_by_aliases(aliases):

                marketplaces = get_item_marketplaces(
                    item_path=alias_field_file_path, item_data=alias_field
                )

                if len(marketplaces) != 1 or marketplaces[0] != "xsoar":
                    alias_field["marketplaces"] = ["xsoar"]
                    click.secho(
                        f"\n================= Updating file {alias_field_file_path} =================",
                        fg="bright_blue",
                    )
                    self._save_alias_field_file(
                        dest_file_path=alias_field_file_path, field_data=alias_field
                    )

    def _get_incident_fields_by_aliases(self, aliases: List[dict]):
        """Get from the id_set the actual fields for the given aliases

        Args:
            aliases (list): The alias list.

        Returns:
            A generator that generates a tuple with the incident field and it's path for each alias in the given list.
        """
        alias_ids: set = {f'incident_{alias.get("cliName")}' for alias in aliases}
        id_set = open_id_set_file(self.id_set_path)
        incident_field_list: list = id_set.get("IncidentFields")

        for incident_field in incident_field_list:
            field_id = list(incident_field.keys())[0]
            if field_id in alias_ids:
                alias_data = incident_field[field_id]
                alias_file_path = alias_data.get("file_path")
                aliased_field, _ = get_dict_from_file(path=alias_file_path)

                yield aliased_field, alias_file_path

    def _save_alias_field_file(
        self,
        dest_file_path: str,
        field_data: str,
        indent: int = 4,
        encode_html_chars: bool = True,
        escape_forward_slashes: bool = False,
        ensure_ascii: bool = False,
    ):
        """Save formatted JSON data to destination file."""
        with open(dest_file_path, "w") as file:
            json.dump(
                field_data,
                file,
                indent=indent,
                encode_html_chars=encode_html_chars,
                escape_forward_slashes=escape_forward_slashes,
                ensure_ascii=ensure_ascii,
            )

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the incident fields JSON updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()
