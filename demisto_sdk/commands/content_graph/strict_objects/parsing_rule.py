from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    DEPRECATED_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictParsingRule(BaseStrictModel):
    id_: str = Field(
        ...,
        alias="id",
        description="Unique identifier of the parsing rule. Used internally to reference this rule.",
    )
    name: str = Field(
        ...,
        description="Display name of the parsing rule shown in the UI.",
    )
    from_version: str = Field(
        ...,
        alias="fromversion",
        description="Minimum platform version required to use this parsing rule (e.g. '6.8.0'). Required field.",
    )
    to_version: Optional[str] = Field(
        None,
        alias="toversion",
        description="Maximum platform version this parsing rule is compatible with. Rule is not loaded on newer platform versions.",
    )
    tags: List[str] = Field(
        ...,
        description="List of dataset tags this parsing rule applies to. Each tag identifies a log source or dataset (e.g. 'vendor_product'). Required.",
    )
    rules: Optional[str] = Field(
        None,
        description="XQL-based parsing rules in YAML format. Defines how raw log data is parsed and structured.",
    )
    samples: Optional[str] = Field(
        None,
        description="Sample raw log data used for testing and validating the parsing rules.",
    )
    comment: Optional[str] = Field(
        None,
        description="Developer comment describing the purpose and usage of this parsing rule.",
    )
    deprecated: Optional[bool] = Field(
        None,
        description="When True, this parsing rule is deprecated and should not be used in new integrations.",
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this parsing rule. Restricts availability to specific modules.",
    )


StrictParsingRule = create_model(
    model_name="StrictParsingRule",
    base_models=(
        _StrictParsingRule,
        NAME_DYNAMIC_MODEL,
        DEPRECATED_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
