from pathlib import Path
from typing import List, Tuple

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects import Mapper
from demisto_sdk.commands.content_graph.objects.base_content import UnknownContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


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

        self.graph = kwargs.get("graph")

    def run_format(self) -> int:
        try:
            logger.info(
                f"\n<blue>================= Updating file {self.source_file} =================</blue>"
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
                f"\n<red>Failed to update file {self.source_file}. Error: {err}</red>"
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
        if not self.graph:
            logger.info(
                f"Skipping formatting of non-existent-fields for {self.source_file} as the no-graph argument was given."
            )
            return

        # get the relevant content item from the graph
        mapper_object: ContentItem
        result = self.graph.search(
            path=Path(self.source_file).relative_to(self.graph.repo_path)
        )
        if not isinstance(result, List) or not result:
            logger.error(f"Failed finding {self.source_file} in the content graph.")
            return
        mapper_object = result[0]
        if not isinstance(mapper_object, Mapper):
            logger.error(
                f"The file {self.source_file} object isn't a mapper, but {type(mapper_object)}."
            )
            return

        # find the fields that aren't in the content repo
        fields_not_in_repo = {
            field.content_item_to.name
            for field in mapper_object.uses
            if isinstance(field.content_item_to, UnknownContent)
        }

        # remove the fields that aren't in the repo
        mapper = self.data.get("mapping", {})

        if fields_not_in_repo:
            logger.info(
                f"Removing the fields {fields_not_in_repo} from the mapper {self.source_file} "
                f"because they aren't in the content repo."
            )

        for mapping_name in mapper.values():
            internal_mapping_fields = mapping_name.get("internalMapping") or {}
            mapping_name["internalMapping"] = {
                inc_name: inc_info
                for inc_name, inc_info in internal_mapping_fields.items()
                if inc_name not in fields_not_in_repo
            }
