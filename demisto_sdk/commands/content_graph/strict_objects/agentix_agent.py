from pydantic import Extra

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AgentixBase,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class Mcp(BaseStrictModel):
    server_url: str


class AgentixAgent(AgentixBase):
    class Config:
        """
        Unknown top-level fields are ignored (not forbidden), so an agent carrying
        a field not yet defined in this schema does not fail ST110.
        """

        extra = Extra.ignore

    color: str
    visibility: str
    actionids: list[str] = []
    skillids: list[str] = []
    systeminstructions: str = ""
    conversationstarters: list[str] = []
    builtinactions: list[str] = []
    autoenablenewactions: bool = False
    roles: list[str] = []
    sharedwithroles: list[str] = []
    knowledgeids: list[str] = []
    mcps: list[Mcp] = []
