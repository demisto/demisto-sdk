from pathlib import Path
from typing import Optional

from pydantic import BaseModel, DirectoryPath, Field, root_validator

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import write_dict
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase
from demisto_sdk.commands.content_graph.strict_objects.agentix_action import (
    ScriptConfig,
)


class AgentixActionArgument(BaseModel):
    name: str
    description: str
    type: str
    required: bool = False
    default_value: Optional[str] = Field(None, alias="defaultvalue")
    hidden: bool = False
    disabled: bool = False
    content_item_arg_name: Optional[str] = Field(None, alias="underlyingargname")
    isgeneratable: bool = False

    @root_validator
    def default_content_item_arg_name(cls, values):
        if values.get("content_item_arg_name") is None:
            values["content_item_arg_name"] = values.get("name")
        return values


class AgentixActionOutput(BaseModel):
    description: str
    type: str
    disabled: bool = False
    content_item_output_name: Optional[str] = Field(
        None, alias="underlyingoutputcontextpath"
    )
    name: str

    @root_validator
    def default_content_item_output_name(cls, values):
        if values.get("content_item_output_name") is None:
            values["content_item_output_name"] = values.get("name")
        return values


class AgentixAction(AgentixBase, content_type=ContentType.AGENTIX_ACTION):
    args: Optional[list[AgentixActionArgument]] = Field(None, exclude=True)
    outputs: Optional[list[AgentixActionOutput]] = Field(None, exclude=True)
    underlying_content_item_id: Optional[str] = None
    underlying_content_item_name: Optional[str] = None
    underlying_content_item_type: str
    underlying_content_item_command: Optional[str] = None
    underlying_content_item_version: int
    requires_user_approval: Optional[bool] = Field(False, alias="requiresuserapproval")
    few_shots: Optional[list[str]] = Field(None, alias="fewshots")
    script_config: Optional[ScriptConfig] = Field(None, alias="script", exclude=True)
    dockerimage: Optional[str] = None

    @root_validator
    def extract_dockerimage(cls, values):
        cfg = values.get("script_config")
        if cfg is not None:
            values["dockerimage"] = cfg.dockerimage
        return values

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if path.suffix not in (".yml", ".yaml"):
            return False
        # Exclude test files
        if path.stem.endswith("_test") or (
            path.stem.startswith("test_") and "test_data" in path.parts
        ):
            return False
        # Regular action: has underlyingcontentitem
        if "underlyingcontentitem" in _dict:
            return True
        # Script action: has script sub-key as a dict, has display (AgentixAction field),
        # and no configuration (which integrations always have)
        if (
            "script" in _dict
            and isinstance(_dict["script"], dict)
            and "display" in _dict
            and "configuration" not in _dict
        ):
            return True
        return False

    @property
    def is_script_action(self) -> bool:
        """True when a .py sibling file exists alongside the action YAML."""
        return (self.path.parent / f"{self.path.stem}.py").exists()

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.PLATFORM,
        **kwargs,
    ) -> dict:
        if self.is_script_action:
            from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
                AgentixActionSplitter,
            )

            processed_data = super().prepare_for_upload(current_marketplace, **kwargs)
            py_code = (self.path.parent / f"{self.path.stem}.py").read_text()
            _, action_dict = AgentixActionSplitter.split(
                self.path, self, py_code, processed_data
            )
            return action_dict
        return super().prepare_for_upload(current_marketplace, **kwargs)

    def dump(self, dir: DirectoryPath, marketplace: MarketplaceVersions) -> None:
        dir.mkdir(exist_ok=True, parents=True)
        if not self.is_script_action:
            super().dump(dir, marketplace)
            return
        from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
            AgentixActionSplitter,
        )

        processed_data = super().prepare_for_upload(marketplace)
        py_code = (self.path.parent / f"{self.path.stem}.py").read_text()
        script_dict, action_dict = AgentixActionSplitter.split(
            self.path, self, py_code, processed_data
        )
        write_dict(dir / self.normalize_name, data=action_dict, handler=self.handler)
        script_name = f"{ContentType.SCRIPT.server_name}-{self.object_id}.yml"
        write_dict(dir / script_name, data=script_dict, handler=self.handler)

    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        summary_res = super().summary(marketplace, incident_to_alert)
        summary_res["underlyingContentItemType"] = self.underlying_content_item_type
        return summary_res
