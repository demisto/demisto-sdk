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
    isgeneratable: bool = False


class AgentixActionOutput(BaseStrictModel):
    description: str
    type: str
    content_item_output_name: str = Field(..., alias="underlyingoutputcontextpath")
    name: str
    disabled: bool = False


class UnderlyingContentItem(BaseStrictModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type: str
    command: Optional[str] = None
    version: str


class AgentixAction(AgentixBase):
    args: Optional[list[AgentixActionArgument]] = None
    outputs: Optional[list[AgentixActionOutput]] = None
    underlying_content_item: UnderlyingContentItem = Field(
        ..., alias="underlyingcontentitem"
    )
    requires_user_approval: bool = Field(False, alias="requiresuserapproval")
    few_shots: Optional[list[str]] = Field(None, alias="fewshots")
