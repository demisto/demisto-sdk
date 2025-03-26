from typing import Any, List, Literal, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class LeftRight(BaseStrictModel):
    value: Any
    is_context: Optional[bool] = Field(None, alias="isContext")


class ArgFilter(BaseStrictModel):
    operator: str
    ignore_case: Optional[bool] = Field(None, alias="ignorecase")
    left: LeftRight
    right: Optional[LeftRight] = None
    type: Optional[str] = None


class StrictField(BaseStrictModel):
    id_: Optional[str] = Field(None, alias="id")
    version: Optional[int] = None
    modified: Optional[str] = None
    field_id: Optional[str] = Field(None, alias="fieldId")
    is_visible: Optional[bool] = Field(None, alias="isVisible")
    sort_values: Optional[str] = Field(None, alias="sortValues")
    filters: Optional[List[ArgFilter]] = None


class Section(BaseStrictModel):
    id_: Optional[str] = Field(None, alias="id")
    version: Optional[int] = None
    modified: Optional[str] = None
    name: Optional[str] = None
    type_: Optional[str] = Field(None, alias="type")
    is_visible: Optional[bool] = Field(None, alias="isVisible")
    read_only: Optional[bool] = Field(None, alias="readOnly")
    description: Optional[str] = None
    query: Optional[Any] = None
    query_type: Optional[str] = Field(None, alias="queryType")
    sort_values: Optional[str] = Field(None, alias="sortValues")
    fields: Optional[List[StrictField]] = None


class TabsAndSections(BaseStrictModel):
    tabs: Optional[List[Any]] = None
    sections: Optional[List[Section]] = None


class StrictCaseLayout(BaseStrictModel):
    id_: str = Field(alias="id")
    group: str = Field(..., enum=["case"])
    definition_id: Optional[str] = Field(None, alias="definitionId")
    version: int
    name: str
    from_version: str = Field(alias="fromVersion")
    to_version: Optional[str] = Field(None, alias="toVersion")
    description: Optional[str] = None
    system: Optional[bool] = None
    marketplaces: Optional[
        List[Literal[MarketplaceVersions.MarketplaceV2, MarketplaceVersions.PLATFORM]]
    ] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
    edit: Optional[TabsAndSections] = None
    indicators_details: Optional[TabsAndSections] = Field(
        None, alias="indicatorsDetails"
    )
    indicators_quick_view: Optional[TabsAndSections] = Field(
        None, alias="indicatorsQuickView"
    )
    quick_view: Optional[TabsAndSections] = Field(None, alias="quickView")
    close: Optional[TabsAndSections] = None
    details: Optional[TabsAndSections] = None
    details_v2: Optional[TabsAndSections] = Field(None, alias="detailsV2")
    mobile: Optional[TabsAndSections] = None
