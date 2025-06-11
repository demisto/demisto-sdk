from pathlib import Path
from typing import Optional

from pydantic import Field, BaseModel

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase


class AgentixActionArgument(BaseModel):
    name: str
    description: str
    type: str
    required: bool = False
    default_value: Optional[str] = Field(None, alias="defaultvalue")
    hidden: bool = False
    disabled: bool = False
    content_item_arg_name: str = Field(..., alias="underlyingargname")


class AgentixActionOutput(BaseModel):
    description: str
    type: str
    disabled: bool = False
    content_item_output_name: str = Field(..., alias="underlyingoutputcontextpath")
    name: str


class AgentixAction(AgentixBase, content_type=ContentType.AGENTIX_ACTION):
    args: Optional[list[AgentixActionArgument]] = Field(None, exclude=True)
    outputs: Optional[list[AgentixActionOutput]] = Field(None, exclude=True)
    agent_id: str = Field(..., alias="agentid")
    underlying_content_item_id: str = Field(..., alias="underlyingcontentitemid")
    underlying_content_item_name: str = Field(..., alias="underlyingcontentitemname")
    underlying_content_item_type: str = Field(..., alias="underlyingcontentitemtype")
    underlying_content_item_version: int = Field(..., alias="underlyingcontentitemversion")
    requires_user_approval: bool = Field(False, alias="requiresuserapproval")
    example_prompts: Optional[list[str]] = Field(None, alias="exampleprompts")

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "agentid" in _dict and path.suffix == ".yml":
            return True
        return False
