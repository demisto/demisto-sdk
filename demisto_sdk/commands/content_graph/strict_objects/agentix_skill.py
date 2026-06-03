from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseStrictModel,
)


class StrictAgentixSkill(BaseStrictModel):
    id_: str = Field(alias="id")
    name: str
    display: Optional[str] = None
    description: str
    content: Optional[str] = None
    internal: Optional[bool] = None
    from_version: Optional[str] = Field(None, alias="fromversion")
    to_version: Optional[str] = Field(None, alias="toversion")
    marketplaces: Optional[List[str]] = None
    supportedModules: Optional[List[str]] = None
