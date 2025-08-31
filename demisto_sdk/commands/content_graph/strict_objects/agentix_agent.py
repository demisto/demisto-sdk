from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AgentixBase,
)


class AgentixAgent(AgentixBase):
    color: str
    actionids: list[str]
    systeminstructions: str
    conversationstarters: list[str]
    autoenablenewactions: bool
