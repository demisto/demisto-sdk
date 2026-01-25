from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
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
    isgeneratable: bool = False


class AgentixActionOutput(BaseModel):
    description: str
    type: str
    disabled: bool = False
    content_item_output_name: str = Field(..., alias="underlyingoutputcontextpath")
    name: str


class AgentixAction(AgentixBase, content_type=ContentType.AGENTIX_ACTION):
    args: Optional[list[AgentixActionArgument]] = Field(None, exclude=True)
    outputs: Optional[list[AgentixActionOutput]] = Field(None, exclude=True)
    underlying_content_item_id: Optional[str] = None
    underlying_content_item_name: Optional[str] = None
    underlying_content_item_type: str
    underlying_content_item_command: Optional[str] = None
    underlying_content_item_version: int
    requires_user_approval: bool = Field(False, alias="requiresuserapproval")
    few_shots: Optional[list[str]] = Field(None, alias="fewshots")
    instructions: Optional[str] = None

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "underlyingcontentitem" in _dict and path.suffix == ".yml":
            return True
        return False

    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        summary_res = super().summary(marketplace, incident_to_alert)
        summary_res["underlyingContentItemType"] = self.underlying_content_item_type
        return summary_res
