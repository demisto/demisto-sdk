from typing import Any, List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    ID_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class ArgFilterSchema(BaseStrictModel):
    operator: str
    ignore_case: Optional[bool] = Field(None, alias="ignorecase")
    left: dict = Field(..., example={"value": Any, "isContext": bool})
    right: Optional[dict] = Field(None, example={"value": Any, "isContext": bool})
    type_: Optional[str] = Field(None, alias="type")


class ArgFiltersSchema(BaseStrictModel):
    __root__: List[ArgFilterSchema]


class _FieldSchema(BaseStrictModel):
    id: Optional[str] = None
    version: Optional[float] = None
    modified: Optional[str] = None
    field_id: Optional[str] = Field(None, alias="fieldId")
    is_visible: Optional[bool] = Field(None, alias="isVisible")
    sort_values: Optional[str] = Field(None, alias="sortValues")
    filters: Optional[List[ArgFiltersSchema]] = None


FieldSchema = create_model(
    model_name="FieldSchema", base_models=(_FieldSchema, ID_DYNAMIC_MODEL)
)


class _SectionSchema(BaseStrictModel):
    id: Optional[str] = None
    version: Optional[float] = None
    modified: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    is_visible: Optional[bool] = Field(None, alias="isVisible")
    read_only: Optional[bool] = Field(None, alias="readOnly")
    description: Optional[str] = None
    query: Optional[Any] = None
    query_type: Optional[str] = Field(None, alias="queryType")
    sort_values: Optional[str] = Field(None, alias="sortValues")
    fields: Optional[List[FieldSchema]] = None  # type:ignore[valid-type]


SectionSchema = create_model(
    model_name="SectionSchema",
    base_models=(
        _SectionSchema,
        ID_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        NAME_DYNAMIC_MODEL,
    ),
)


class TabsSchema(BaseStrictModel):
    __root__: Any  # Assuming tabs can be any type


class MappingSchema(BaseStrictModel):
    tabs: Optional[List[TabsSchema]] = None
    sections: Optional[List[SectionSchema]] = None  # type:ignore[valid-type]


class _StrictLayout(BaseStrictModel):
    """
    This is the layout-container item in Content repo.
    Since there are no layouts in Content, StrictLayout is for layout-container same like the graph.
    """
    id: str
    group: str = Field(..., enum=["incident", "indicator", "case"])
    definition_id: Optional[str] = Field(None, alias="definitionId")
    version: float
    name: str
    from_version: str = Field(..., alias="fromVersion")
    to_version: Optional[str] = Field(None, alias="toVersion")
    description: Optional[str] = None
    system: Optional[bool] = None
    marketplaces: Optional[List[str]] = Field(
        None, enum=[market_place.value for market_place in MarketplaceVersions]
    )
    edit: Optional[MappingSchema] = None
    indicators_details: Optional[MappingSchema] = Field(None, alias="indicatorsDetails")
    indicators_quick_view: Optional[MappingSchema] = Field(
        None, alias="indicatorsQuickView"
    )
    quick_view: Optional[MappingSchema] = Field(None, alias="quickView")
    close: Optional[MappingSchema] = None
    details: Optional[MappingSchema] = None
    details_v2: Optional[MappingSchema] = Field(None, alias="detailsV2")
    mobile: Optional[MappingSchema] = None


StrictLayout = create_model(
    model_name="StrictLayout",
    base_models=(
        _StrictLayout,
        DESCRIPTION_DYNAMIC_MODEL,
        NAME_DYNAMIC_MODEL,
        ID_DYNAMIC_MODEL,
    ),
)
