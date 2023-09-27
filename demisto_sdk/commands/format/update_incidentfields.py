from typing import List, Tuple

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    OLDEST_INCIDENT_FIELD_SUPPORTED_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


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
        **kwargs,
    ):
        super().__init__(
            input=input,
            output=output,
            path=path,
            from_version=from_version,
            no_validate=no_validate,
            **kwargs,
        )
        self.graph = kwargs.get("graph")

    def run_format(self) -> int:
        try:
            logger.info(
                f"\n[blue]================= Updating file {self.source_file} =================[/blue]"
            )
            super().update_json()
            self.format_marketplaces_field_of_aliases()
            self.set_default_values_as_needed()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            logger.debug(
                f"\n[red]Failed to update file {self.source_file}. Error: {err}[/red]"
            )
            return ERROR_RETURN_CODE

    def format_marketplaces_field_of_aliases(self):
        """
        When formatting incident field with aliases,
        the function will update the marketplaces in the fields mapped by the aliases to be XSOAR marketplace only.
        """

        aliases = self.data.get("Aliases", {})
        if aliases:

            if not self.graph:
                logger.info(
                    f"Skipping formatting of marketplaces field of aliases for {self.source_file} as the "
                    f"no-graph argument was given."
                )
                return

            for item in self._get_incident_fields_by_aliases(aliases):
                alias_marketplaces = item.marketplaces
                alias_file_path = item.path
                alias_toversion = Version(item.toversion)

                if alias_toversion > Version(
                    OLDEST_INCIDENT_FIELD_SUPPORTED_VERSION
                ) and (
                    len(alias_marketplaces) != 1
                    or alias_marketplaces[0] != MarketplaceVersions.XSOAR.value
                ):

                    logger.info(
                        f"\n[blue]================= Updating file {alias_file_path} =================[/blue]"
                    )
                    alias_file_content = get_file(alias_file_path, raise_on_error=True)
                    alias_file_content["marketplaces"] = [
                        MarketplaceVersions.XSOAR.value
                    ]

                    self._save_alias_field_file(
                        dest_file_path=alias_file_path, field_data=alias_file_content
                    )

    def _get_incident_fields_by_aliases(self, aliases: List[dict]) -> list:
        """
        Get from the graph the actual fields for the given aliases

        Args:
            aliases (list): The alias list.

        Returns:
            list: A list of dictionaries, each dictionary represent an incident field.
        """
        alias_ids: set = {f'{alias.get("cliName")}' for alias in aliases}
        return (
            self.graph.search(
                cli_name=alias_ids,
                content_type=ContentType.INCIDENT_FIELD,
            )
            if self.graph
            else []
        )

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
