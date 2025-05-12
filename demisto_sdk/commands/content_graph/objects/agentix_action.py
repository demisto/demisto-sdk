from pathlib import Path
from typing import Optional

from pydantic import Field, BaseModel

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase


class AgentixActionArgument(BaseModel):
    name: str
    description: str
    arg_type: int = Field(..., alias="argType")
    required: bool = False
    default_value: Optional[str] = Field(None, alias="defaultValue")
    hidden: bool = False
    content_item_arg_name: str = Field(..., alias="underlyingContentItemInputName")


class AgentixActionOutput(BaseModel):
    display: str
    description: str
    type: str
    content_item_output_name: str = Field(..., alias="underlyingContentItemOutputName")


class AgentixAction(AgentixBase, content_type=ContentType.AGENTIX_ACTION):
    args: Optional[list[AgentixActionArgument]] = Field(None, exclude=True)
    outputs: Optional[list[AgentixActionOutput]] = Field(None, exclude=True)
    few_shots: Optional[str] = Field(None, alias="fewShots")
    agent_id: str = Field(..., alias="agentId")
    underlying_content_item_id: str = Field(..., alias="underlyingContentItemId")
    underlying_content_item_name: str = Field(..., alias="underlyingContentItemName")
    underlying_content_item_type: int = Field(..., alias="underlyingContentItemType")
    underlying_content_item_version: int = Field(..., alias="underlyingContentItemVersion")
    requires_user_approval: bool = Field(False, alias="requiresUserApproval")

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        pass
