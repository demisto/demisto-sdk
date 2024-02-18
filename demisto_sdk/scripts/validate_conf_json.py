from collections import defaultdict
from pathlib import Path

from demisto_sdk.commands.common.content_constant_paths import CONF_PATH
from demisto_sdk.commands.common.logger import logger, logging_setup
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.conf_json import ConfJSON


class ConfJsonValidator:
    def __init__(self, conf_json_path: Path = CONF_PATH) -> None:
        self.conf = ConfJSON.from_path(conf_json_path)

        # Instantiate and query relevant data from the graph
        update_content_graph(graph := ContentGraphInterface())
        self.graph_ids_by_type = {
            content_type: graph.search(content_type=content_type, object_id=conf_ids)
            for content_type, conf_ids in self.conf.linked_content_items.items()
        }

    def _validate_content_exists(self) -> bool:
        missing = defaultdict(set)

        for content_type, ids in self.conf.linked_content_items.items():
            if found_missing := ids.difference(
                {
                    item.object_id
                    for item in self.graph_ids_by_type.get(content_type, ())
                }
            ):
                logger.error(
                    f"Found {len(found_missing)} {content_type.value} IDs missing from the content graph: {sorted(found_missing)}"
                )
                missing[content_type] = found_missing

        return not bool(missing)

    def _validate_content_not_deprecated(self) -> bool:
        deprecated = defaultdict(set)

        for content_type, ids in self.conf.linked_content_items.items():
            graph_ids = {
                item.object_id
                for item in self.graph_ids_by_type.get(content_type, ())
                if item.deprecated
            }
            if found_deprecated := ids.intersection(graph_ids):
                logger.error(
                    f"Found {len(found_deprecated)} deprecated {content_type.value} items: {sorted(found_deprecated)}"
                )
                deprecated[content_type] = found_deprecated

        return not bool(deprecated)

    def validate(self):
        return all(
            (
                self._validate_content_exists(),
                self._validate_content_not_deprecated(),
            )
        )


if __name__ == "__main__":
    logging_setup()
    if not ConfJsonValidator().validate():
        logger.error("conf.json is not valid")
        exit(1)
    logger.info("[green]conf.json is valid[/green]")
