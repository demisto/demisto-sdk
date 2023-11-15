from typing import ClassVar

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator


class GraphValidator(BaseValidator):
    graph_initialized: ClassVar[bool] = False
    graph: ClassVar[ContentGraphInterface]
    validate_graph: ClassVar[bool] = True

    @property
    def graph(self):
        if not self.graph_initialized:
            logger.info("Graph validations were selected, will init graph")
            self.graph_initialized = True
            self.graph = ContentGraphInterface()
            update_content_graph(
                self.graph,
                use_git=True,
                output_path=self.graph,
            )
        return self.graph
