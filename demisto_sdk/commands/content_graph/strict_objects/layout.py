from typing import Any, Dict, List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    ID_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class ArgFilter(BaseStrictModel):
    operator: str
    ignore_case: Optional[bool] = Field(None, alias="ignorecase")
    left: dict = Field(..., example={"value": Any, "isContext": bool})
    right: Optional[dict] = Field(None, example={"value": Any, "isContext": bool})
    type_: Optional[str] = Field(None, alias="type")


class ArgFilters(BaseStrictModel):
    __root__: List[ArgFilter]


class _SectionField(BaseStrictModel):
    id: Optional[str] = None
    version: Optional[float] = None
    modified: Optional[str] = None
    field_id: Optional[str] = Field(None, alias="fieldId")
    is_visible: Optional[bool] = Field(None, alias="isVisible")
    sort_values: Optional[str] = Field(None, alias="sortValues")
    filters: Optional[List[ArgFilters]] = None


SectionField = create_model(
    model_name="SectionField", base_models=(_SectionField, ID_DYNAMIC_MODEL)
)


class _Section(BaseStrictModel):
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
    fields: Optional[List[SectionField]] = None  # type:ignore[valid-type]


Section = create_model(
    model_name="Section",
    base_models=(
        _Section,
        ID_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        NAME_DYNAMIC_MODEL,
    ),
)


class Tabs(BaseStrictModel):
    id_: str = Field(alias="id")
    type_: str = Field(alias="type")
    name: str
    sections: Optional[List[Dict[str, Any]]] = None
    hidden: Optional[str] = None
    filters: Optional[Any] = None
    show_empty_fields: Optional[bool] = Field(None, alias="showEmptyFields")
    report: Optional[bool] = None
    read_only: Optional[bool] = Field(None, alias="readOnly")
    roles: Optional[List[str]] = None
    mobile_hidden: Optional[bool] = Field(None, alias="mobileHidden")
    web_hidden: Optional[bool] = Field(None, alias="webHidden")


class Mapping(BaseStrictModel):
    tabs: Optional[List[Tabs]] = None  # type:ignore[valid-type]
    sections: Optional[List[Section]] = None  # type:ignore[valid-type]


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
    marketplaces: Optional[List[MarketplaceVersions]] = None
    edit: Optional[Mapping] = None
    indicators_details: Optional[Mapping] = Field(None, alias="indicatorsDetails")
    indicators_quick_view: Optional[Mapping] = Field(None, alias="indicatorsQuickView")
    quick_view: Optional[Mapping] = Field(None, alias="quickView")
    close: Optional[Mapping] = None
    details: Optional[Mapping] = None
    details_v2: Optional[Mapping] = Field(None, alias="detailsV2")
    mobile: Optional[Mapping] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")


StrictLayout = create_model(
    model_name="StrictLayout",
    base_models=(
        _StrictLayout,
        DESCRIPTION_DYNAMIC_MODEL,
        NAME_DYNAMIC_MODEL,
        ID_DYNAMIC_MODEL,
    ),
)
