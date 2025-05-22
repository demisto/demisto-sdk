from typing import Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AgentixBase,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class AgentixActionArgument(BaseStrictModel):
    name: str
    description: str
    type: str
    required: bool = False
    default_value: Optional[str] = Field(None, alias="defaultValue")
    hidden: bool = False
    content_item_arg_name: str = Field(..., alias="underlyingContentItemInputName")
    generatable: bool = False


class AgentixActionOutput(BaseStrictModel):
    name: str
    description: str
    type: str
    content_item_output_name: str = Field(..., alias="underlyingContentItemOutputName")

class AgentixAction(AgentixBase):
    args: Optional[list[AgentixActionArgument]] = None
    outputs: Optional[list[AgentixActionOutput]] = None
    few_shots: Optional[str] = Field(None, alias="fewShots")
    agent_id: str = Field(..., alias="agentId")
    underlying_content_item_id: str = Field(..., alias="underlyingContentItemId")
    underlying_content_item_name: str = Field(..., alias="underlyingContentItemName")
    underlying_content_item_type: int = Field(..., alias="underlyingContentItemType")
    underlying_content_item_version: int = Field(..., alias="underlyingContentItemVersion")
    requires_user_approval: bool = Field(False, alias="requiresUserApproval")
