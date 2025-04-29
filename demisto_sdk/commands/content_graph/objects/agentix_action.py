from pathlib import Path
from typing import Optional

from pydantic import Field, BaseModel

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase


class AgentixActionArgument(BaseModel):
    display: str = Field(..., alias="name")
    description: str
    arg_type: int = Field(..., alias="argType")
    required: bool = Field(..., alias="required")
    default_value: Optional[str] = Field(None, alias="defaultValue")
    is_hidden: bool = Field(..., alias="isHidden")
    content_item_arg_name: str = Field(..., alias="contentItemArgName")
    is_details_overridden: bool = Field(..., alias="isDetailsOverridden")


class AgentixActionOutput(BaseModel):
    display: str = Field(..., alias="name")
    description: str
    output_type: str = Field(..., alias="outputType")
    content_item_output_name: str = Field(..., alias="contentItemOutputName")
    is_details_overridden: bool = Field(..., alias="isDetailsOverridden")


class AgentixAction(AgentixBase, content_type=ContentType.AGENTIX_ACTION):
    arguments: Optional[list[AgentixActionArgument]] = None
    outputs: Optional[list[AgentixActionOutput]] = None
    few_shots: Optional[str] = Field(None, alias="fewShots")
    agent_id: str = Field(..., alias="agentId")
    content_item_id: str = Field(..., alias="contentItemId")
    content_item_type: str = Field(..., alias="contentItemType")
    content_item_version: str = Field(..., alias="contentItemVersion")
    content_item_version: str = Field(..., alias="contentItemPackVersion")

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        pass
