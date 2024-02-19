from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.content_constant_paths import CONF_PATH
from demisto_sdk.commands.common.logger import logger, logging_setup
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.conf_json import ConfJSON


class ConfJsonValidator:
    def __init__(
        self,
        conf_json_path: Path = CONF_PATH,
        graph: Optional[ContentGraphInterface] = None,  # Pass None to generate
    ) -> None:
        self.conf = ConfJSON.from_path(conf_json_path)

        logger.info("Creating content graph - this may take a few minutes")
        if graph is None:
            update_content_graph(graph := ContentGraphInterface())
        self.graph_ids_by_type = {
            content_type: graph.search(content_type=content_type, object_id=conf_ids)
            for content_type, conf_ids in self.conf.linked_content_items.items()
        }
        logger.info(f"{self.graph_ids_by_type.keys()=}")

    def _validate_content_exists(self) -> bool:
        is_valid = True

        for content_type, ids in self.conf.linked_content_items.items():
            if found_missing := ids.difference(
                {
                    item.object_id
                    for item in self.graph_ids_by_type.get(content_type, ())
                }
            ):
                logger.error(
                    f"{len(found_missing)} {content_type.value}s are not found in the graph: {','.join(sorted(found_missing))}"
                )
                is_valid = False
        return is_valid

    def _validate_content_not_deprecated(self) -> bool:
        is_valid = True

        for content_type, ids in self.conf.linked_content_items.items():
            deprecated_ids = {
                item.object_id
                for item in self.graph_ids_by_type.get(content_type, ())
                if getattr(item, "deprecated", False)
            }
            if found_deprecated := ids.intersection(deprecated_ids):
                logger.error(
                    f"{len(found_deprecated)} {content_type.value}s are deprecated: {','.join(sorted(found_deprecated))}"
                )
                is_valid = False

        return is_valid

    def validate(self) -> bool:
        return all(
            (
                self._validate_content_exists(),
                self._validate_content_not_deprecated(),
            )
        )


def main():
    logging_setup()
    if not ConfJsonValidator().validate():
        logger.error("conf.json is not valid")
        exit(1)
    logger.info("[green]conf.json is valid[/green]")


if __name__ == "__main__":
    main()
