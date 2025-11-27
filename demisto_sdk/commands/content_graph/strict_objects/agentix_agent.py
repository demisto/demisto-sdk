from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AgentixBase,
)


class AgentixAgent(AgentixBase):
    color: str
    visibility: str
    actionids: list[str] = []
    systeminstructions: str = ""
    conversationstarters: list[str] = []
    builtinactions: list[str] = []
    autoenablenewactions: bool = False
    roles: list[str] = []
    sharedwithroles: list[str] = []
