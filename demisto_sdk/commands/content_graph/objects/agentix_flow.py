from pathlib import Path
from typing import Any, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import AGENTIX_FLOWS_DIR
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase


class AgentixFlow(AgentixBase, content_type=ContentType.AGENTIX_FLOW):
    """Represents an AgentixFlow content item.

    Flows live under ``Packs/<PackName>/AgentixFlows/<FlowName>/<FlowName>.yml``
    with a top-level ``id`` and ``version`` (no ``commonfields``) and an opaque
    ``definition`` block.
    """

    # Nested map: excluded from graph nodes (Neo4j properties must be primitives).
    # Packaging re-reads the YAML from disk, so it is still shipped in artifacts.
    definition: Optional[Any] = Field(None, exclude=True)
    supportedModules: Optional[list[str]] = None

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        """Match an AgentixFlow ``<FlowName>.yml`` file under ``AgentixFlows/``."""
        if (
            path.suffix in {".yml", ".yaml"}
            and not path.stem.endswith("_test")
            and AGENTIX_FLOWS_DIR in path.parts
        ):
            return True
        return False
