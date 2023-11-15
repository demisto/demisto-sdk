from typing import ClassVar

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator


class GraphValidator(BaseValidator):
    graph_initialized = False
    validate_graph: ClassVar[bool] = True
    graph_interface: ContentGraphInterface

    @property
    def graph(self) -> ContentGraphInterface:
        if not self.graph_initialized:
            logger.info("Graph validations were selected, will init graph")
            self.graph_initialized = True
            self.graph_interface = ContentGraphInterface()
            update_content_graph(
                self.graph_interface,
                use_git=True,
            )
        return self.graph_interface
