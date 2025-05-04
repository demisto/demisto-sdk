from typing import Optional

from pydantic import Field, create_model

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AgentixBase,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class AgentixActionArgument(BaseStrictModel):
    display: str = Field(..., alias="name")  # TODO - alias
    description: str
    arg_type: int = Field(..., alias="argType")  # TODO - (0 (text??) undefined, 1 unknown, 2 key/value, 3 text area)
    required: bool = Field(..., alias="required")  # TODO - required or isMandatory
    default_value: Optional[str] = Field(None, alias="defaultValue")
    is_hidden: bool = Field(..., alias="isHidden")
    content_item_arg_name: str = Field(..., alias="contentItemArgName")
    is_details_overridden: bool = Field(..., alias="isDetailsOverridden")


class AgentixActionOutput(BaseStrictModel):
    display: str = Field(..., alias="name")  # TODO - alias
    description: str
    output_type: str = Field(..., alias="outputType")  # TODO - on our side is a str like String, List and etc
    content_item_output_name: str = Field(..., alias="contentItemOutputName")
    is_details_overridden: bool = Field(..., alias="isDetailsOverridden")

class AgentixAction(AgentixBase):
    args: Optional[list[AgentixActionArgument]] = None
    outputs: Optional[list[AgentixActionOutput]] = None
    few_shots: Optional[str] = Field(None, alias="fewShots")
    agent_id: str = Field(..., alias="agentId")
    underlying_content_item_id: str = Field(..., alias="underlyingContentItemId")
    underlying_content_item_name: str = Field(..., alias="underlyingContentItemName")
    underlying_content_item_type: int = Field(..., alias="underlyingContentItemType") # (1 script, 2 playbook, 3 command, 4 AI task)
    underlying_content_item_version: int = Field(..., alias="underlyingContentItemVersion") # TODO - int vs str
    content_item_pack_version: str = Field(..., alias="underlyingContentItemPackVersion")
