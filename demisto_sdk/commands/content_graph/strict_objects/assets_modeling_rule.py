from typing import Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    DEPRECATED_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictAssetsModelingRule(BaseStrictModel):
    id_: str = Field(alias="id")
    name: str
    from_version: str = Field(alias="fromversion")
    to_version: Optional[str] = Field(None, alias="toversion")
    tags: Optional[str] = None
    rules: Optional[str] = None
    schema_: Optional[str] = Field(None, alias="schema")  # key_word
    comment: Optional[str] = None
    deprecated: Optional[bool] = None


StrictAssetsModelingRule = create_model(
    model_name="StrictAssetsModelingRule",
    base_models=(
        _StrictAssetsModelingRule,
        NAME_DYNAMIC_MODEL,
        DEPRECATED_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
