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
    default_value: Optional[str] = Field(None, alias="defaultvalue")
    hidden: bool = False
    disabled: bool = False
    content_item_arg_name: str = Field(..., alias="underlyingargname")
    generatable: bool = False


class AgentixActionOutput(BaseStrictModel):
    description: str
    type: str
    content_item_output_name: str = Field(..., alias="underlyingoutputcontextpath")
    name: str
    disabled: bool = False

class AgentixAction(AgentixBase):
    args: Optional[list[AgentixActionArgument]] = None
    outputs: Optional[list[AgentixActionOutput]] = None
    agent_id: str = Field(..., alias="agentid")
    underlying_content_item_id: str = Field(..., alias="underlyingcontentitemid")
    underlying_content_item_name: str = Field(..., alias="underlyingcontentitemname")
    underlying_content_item_type: str = Field(..., alias="underlyingcontentitemtype")
    underlying_content_item_version: int = Field(..., alias="underlyingcontentitemversion")
    requires_user_approval: bool = Field(False, alias="requiresuserapproval")
    example_prompts: Optional[list[str]] = Field(None, alias="exampleprompts")
