from typing import Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AgentixBase,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class AgentixActionArgument(BaseStrictModel):
    name: str = Field(
        ...,
        description="Unique identifier for this argument as it appears in the action definition. Must match the underlying content item's argument name.",
    )
    description: str = Field(
        ...,
        description="Human-readable explanation of what this argument represents and how it should be used by the AI agent.",
    )
    type: str = Field(
        ...,
        description="Data type of the argument (e.g. 'String', 'Number', 'Boolean', 'Date'). Must be a valid XSOAR field type.",
    )
    required: bool = Field(
        False,
        description="Whether this argument must be supplied when invoking the action. Defaults to False (optional).",
    )
    default_value: Optional[str] = Field(
        None,
        alias="defaultvalue",
        description="Default value used for this argument when none is provided by the caller. Only applicable when required=False.",
    )
    hidden: bool = Field(
        False,
        description="When True, the argument is hidden from the UI and cannot be set by users directly. Defaults to False.",
    )
    disabled: bool = Field(
        False,
        description="When True, the argument is disabled and cannot be set or overridden. Defaults to False.",
    )
    content_item_arg_name: str = Field(
        ...,
        alias="underlyingargname",
        description="The exact name of the corresponding argument in the underlying content item (integration command or script). Must match exactly.",
    )
    isgeneratable: bool = Field(
        False,
        description="When True, the AI agent can auto-generate a value for this argument based on context. Defaults to False.",
    )


class AgentixActionOutput(BaseStrictModel):
    description: str = Field(
        ...,
        description="Human-readable explanation of what this output field represents and what data it contains.",
    )
    type: str = Field(
        ...,
        description="Data type of the output (e.g. 'String', 'Number', 'Boolean', 'Date'). Must be a valid XSOAR field type.",
    )
    content_item_output_name: str = Field(
        ...,
        alias="underlyingoutputcontextpath",
        description="The context path of the corresponding output in the underlying content item (e.g. 'IP.Address'). Must match exactly.",
    )
    name: str = Field(
        ...,
        description="Unique name of the output field as it appears in the action definition.",
    )
    disabled: bool = Field(
        False,
        description="When True, this output is disabled and will not be returned by the action. Defaults to False.",
    )


class UnderlyingContentItem(BaseStrictModel):
    id: Optional[str] = Field(
        None,
        description="Unique identifier of the underlying content item (integration or script). Used to resolve the exact item when name is ambiguous.",
    )
    name: Optional[str] = Field(
        None,
        description="Display name of the underlying content item (integration or script name).",
    )
    type: str = Field(
        ...,
        description="Type of the underlying content item. Must be one of: 'integration', 'script'.",
    )
    command: Optional[str] = Field(
        None,
        description="Specific command name within the underlying integration to invoke. Required when type is 'integration'. Leave empty for scripts.",
    )
    version: str = Field(
        ...,
        description="Version of the underlying content item this action is bound to (e.g. '-1' for latest).",
    )


class AgentixAction(AgentixBase):
    display: str = Field(
        ...,
        description="Human-readable display name of the action shown in the UI and to the AI agent. Should be concise and descriptive.",
    )
    args: Optional[list[AgentixActionArgument]] = Field(
        None,
        description="List of input arguments accepted by this action. Each argument maps to a parameter of the underlying content item.",
    )
    outputs: Optional[list[AgentixActionOutput]] = Field(
        None,
        description="List of output fields returned by this action. Each output maps to a context path of the underlying content item.",
    )
    underlying_content_item: UnderlyingContentItem = Field(
        ...,
        alias="underlyingcontentitem",
        description="The content item (integration command or script) that this action wraps. Defines what gets executed when the action is invoked.",
    )
    requires_user_approval: bool = Field(
        False,
        alias="requiresuserapproval",
        description="When True, the action requires explicit user approval before execution. Use for destructive or sensitive operations. Defaults to False.",
    )
    few_shots: Optional[list[str]] = Field(
        None,
        alias="fewshots",
        description="Optional list of few-shot example prompts to guide the AI agent when deciding to invoke this action.",
    )
