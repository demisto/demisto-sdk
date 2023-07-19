from typing import Tuple

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface as ContentGraphInterface,
)


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

        self.graph = ContentGraphInterface(should_update=True)  # TODO Remove the should_update

    def run_format(self) -> int:
        try:
            logger.info(
                f"\n[blue]================= Updating file {self.source_file} =================[/blue]"
            )
            super().update_json()
            self.set_description()
            self.set_mapping()
            self.update_id()
            self.remove_non_existent_fields()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE

        except Exception as err:
            logger.debug(
                f"\n[red]Failed to update file {self.source_file}. Error: {err}[/red]"
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
        # get the relevant content item from the graph
        results = self.graph.search(object_id=self.data.get('id', ''))
        mapper_node = {}
        for result in results:
            if result.content_type == ContentType.MAPPER and str(result.path) == self.source_file:
                mapper_node = result
                break

        # find the fields that aren't in the content repo
        fields_not_in_repo = []
        for field in mapper_node.uses:
            if field.content_item_to.not_in_repository:
                fields_not_in_repo.append(field.content_item_to.name)

        # remove the fields that aren't in the repo
        mapper = self.data.get("mapping", {})

        for mapping_name in mapper.values():
            internal_mapping_fields = mapping_name.get("internalMapping") or {}
            mapping_name["internalMapping"] = {
                inc_name: inc_info
                for inc_name, inc_info in internal_mapping_fields.items()
                if inc_name
                not in fields_not_in_repo
            }
