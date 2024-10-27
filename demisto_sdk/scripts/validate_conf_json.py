import os
from pathlib import Path
from typing import List, Optional, cast

from demisto_sdk.commands.common.content_constant_paths import CONF_PATH
from demisto_sdk.commands.common.logger import logger, logging_setup
from demisto_sdk.commands.common.tools import string_to_bool
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.base_content import UnknownContent
from demisto_sdk.commands.content_graph.objects.conf_json import ConfJSON
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class ConfJsonValidator:
    def __init__(
        self,
        conf_json_path: Path = CONF_PATH,
        graph: Optional[ContentGraphInterface] = None,  # Pass None to generate
    ) -> None:
        self._conf_path = conf_json_path
        self.conf = ConfJSON.from_path(conf_json_path)

        logger.info("Creating content graph - this may take a few minutes")
        if graph is None:
            update_content_graph(graph := ContentGraphInterface())
        self.graph_ids_by_type = {
            content_type: cast(
                List[ContentItem],
                [
                    item
                    for item in graph.search(
                        content_type=content_type, object_id=conf_ids
                    )
                    if not isinstance(
                        item, UnknownContent
                    )  # UnknownContent items are artificially generated in relationships, are not part of the repo
                ],
            )
            for content_type, conf_ids in self.conf.linked_content_items.items()
        }

    def _validate_content_exists(self) -> bool:
        is_valid = True

        for content_type, linked_ids in self.conf.linked_content_items.items():
            if linked_ids_missing_in_graph := linked_ids.difference(
                {
                    item.object_id
                    for item in self.graph_ids_by_type.get(content_type, ())
                }
            ):
                message = f"{len(linked_ids_missing_in_graph)} {content_type.value}s are not found in the graph: {','.join(sorted(linked_ids_missing_in_graph))}"
                logger.error(message)
                if string_to_bool(os.getenv("GITHUB_ACTIONS", False)):
                    print(  # noqa: T201
                        f"::error file={self._conf_path},line=1,endLine=1,title=Conf.JSON Error::{message}"
                    )

                is_valid = False
        return is_valid

    def validate(self) -> bool:
        return self._validate_content_exists()


def main():
    logging_setup(calling_function=Path(__file__).stem)
    if not ConfJsonValidator().validate():
        logger.error("conf.json is not valid")
        exit(1)
    logger.info("<green>conf.json is valid</green>")


if __name__ == "__main__":
    main()
