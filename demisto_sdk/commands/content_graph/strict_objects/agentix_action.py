from typing import Optional

from pydantic import Field, root_validator

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
    content_item_arg_name: Optional[str] = Field(None, alias="underlyingargname")
    isgeneratable: bool = False

    @root_validator
    def default_content_item_arg_name(cls, values):
        if values.get("content_item_arg_name") is None:
            values["content_item_arg_name"] = values.get("name")
        return values


class AgentixActionOutput(BaseStrictModel):
    description: str
    type: str
    content_item_output_name: Optional[str] = Field(
        None, alias="underlyingoutputcontextpath"
    )
    name: str
    disabled: bool = False

    @root_validator
    def default_content_item_output_name(cls, values):
        if values.get("content_item_output_name") is None:
            values["content_item_output_name"] = values.get("name")
        return values


class UnderlyingContentItem(BaseStrictModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type: str
    command: Optional[str] = None
    version: str


class ScriptConfig(BaseStrictModel):
    """Script configuration for script actions. Only explicitly listed fields are allowed.
    Unknown fields are rejected (BaseStrictModel has extra=Extra.forbid).

    Fields:
        dockerimage: Required. Docker image for the generated script.
        standalone: Optional. When True, the generated script is NOT internal (visible in UI).
                    When False or None (default), the generated script IS internal (hidden).
        runonce: Optional. Maps to StrictScript.runonce.
        run_as: Optional. Maps to StrictScript.runas (the role the script runs as).
        depends_on: Optional. Maps to StrictScript.dependson (script dependencies).
    """

    dockerimage: str  # required
    standalone: Optional[bool] = None
    runonce: Optional[bool] = None
    run_as: Optional[str] = Field(None, alias="runas")
    depends_on: Optional[dict] = Field(None, alias="dependson")


class AgentixAction(AgentixBase):
    display: str
    args: Optional[list[AgentixActionArgument]] = None
    outputs: Optional[list[AgentixActionOutput]] = None
    underlying_content_item: Optional[UnderlyingContentItem] = Field(
        None, alias="underlyingcontentitem"
    )
    script: Optional[ScriptConfig] = None  # presence → script action
    requires_user_approval: bool = Field(False, alias="requiresuserapproval")
    few_shots: Optional[list[str]] = Field(None, alias="fewshots")

    @root_validator
    def validate_script_action_constraints(cls, values):
        has_underlying = values.get("underlying_content_item") is not None
        has_script = values.get("script") is not None
        if not has_underlying and not has_script:
            raise ValueError(
                "Either 'underlyingcontentitem' or 'script' (dict) must be provided. "
                "'script' as a dict indicates a script action."
            )
        return values
