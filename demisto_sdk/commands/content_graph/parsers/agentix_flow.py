from functools import cached_property

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.agentix_base import (
    AgentixBaseParser,
)
from demisto_sdk.commands.content_graph.strict_objects.agentix_flow import (
    StrictAgentixFlow,
)


class AgentixFlowParser(AgentixBaseParser, content_type=ContentType.AGENTIX_FLOW):
    """Parser for AgentixFlow content items.

    An AgentixFlow lives at ``Packs/<PackName>/AgentixFlows/<FlowName>/<FlowName>.yml``.
    Unlike the other Agentix types, the item has a top-level ``id`` and
    ``version`` (no ``commonfields`` block). Only the YAML is parsed; the
    companion ``<FlowName>_flow.json`` and ``src/`` code are packaged at dump
    time by ``AgentixFlow.dump``.
    """

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {"object_id": "id", "version": "version", "display": "name"}
        )
        return super().field_mapping

    @property
    def strict_object(self):
        return StrictAgentixFlow
