from typing import Optional

from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel
from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import AgentixBase


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
    arguments: Optional[list[AgentixActionArgument]] = None
    outputs: Optional[list[AgentixActionOutput]] = None
    few_shots: Optional[str] = Field(None, alias="fewShots")
    agent_id: str = Field(..., alias="agentId")
    content_item_id: str = Field(..., alias="contentItemId")
    content_item_type: str = Field(..., alias="contentItemType")  # (1 script, 2 playbook, 3 command, 4 AI task)
    content_item_version: str = Field(..., alias="contentItemVersion")  # TODO - int vs str
