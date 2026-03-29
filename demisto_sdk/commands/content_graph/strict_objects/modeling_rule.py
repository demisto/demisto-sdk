from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    DEPRECATED_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictModelingRule(BaseStrictModel):
    id_: str = Field(
        ...,
        alias="id",
        description="Unique identifier of the modeling rule. Used internally to reference this rule.",
    )
    name: str = Field(
        ...,
        description="Display name of the modeling rule shown in the UI.",
    )
    from_version: str = Field(
        ...,
        alias="fromversion",
        description="Minimum platform version required to use this modeling rule (e.g. '6.8.0'). Required field.",
    )
    to_version: Optional[str] = Field(
        None,
        alias="toversion",
        description="Maximum platform version this modeling rule is compatible with. Rule is not loaded on newer platform versions.",
    )
    tags: Optional[str] = Field(
        None,
        description="Comma-separated tags used to categorize and filter this modeling rule.",
    )
    rules: Optional[str] = Field(
        None,
        description="XDM (XDR Data Model) mapping rules in YAML format. Defines how raw log fields are mapped to XDM schema fields.",
    )
    schema_: Optional[str] = Field(
        None,
        alias="schema",
        description="JSON schema definition for the raw log data this modeling rule processes. Validates incoming data structure.",
    )
    comment: Optional[str] = Field(
        None,
        description="Developer comment describing the purpose and usage of this modeling rule.",
    )
    deprecated: Optional[bool] = Field(
        None,
        description="When True, this modeling rule is deprecated and should not be used in new integrations.",
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this modeling rule. Restricts availability to specific modules.",
    )


StrictModelingRule = create_model(
    model_name="StrictModelingRule",
    base_models=(
        _StrictModelingRule,
        NAME_DYNAMIC_MODEL,
        DEPRECATED_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
