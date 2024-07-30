from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    ID_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
    create_dynamic_model,
    create_model,
)


class _DashboardLayout(BaseStrictModel):
    force_range: bool = Field(alias="forceRange")
    x: int
    y: int
    h: int
    w: int
    i: str
    widget: dict = Field(default_factory=dict)
    reflect_dimensions: Optional[bool] = Field(None, alias="reflectDimensions")


DashboardLayout = create_model(
    model_name="DashboardLayout",
    base_models=(
        _DashboardLayout,
        ID_DYNAMIC_MODEL,
    ),
)


class _StrictDashboard(BaseStrictModel):
    id: str
    version: int
    name: str
    description: str
    from_date_license: Optional[str] = Field(None, alias="fromDateLicense")
    is_predefined: bool = Field(alias="isPredefined")
    from_date: Optional[str] = Field(None, alias="fromDate")
    to_date: Optional[str] = Field(None, alias="toDate")
    period: Optional[dict] = Field(default_factory=dict)
    layout: Optional[List[DashboardLayout]] = Field(default_factory=list)  # type:ignore[valid-type]
    marketplaces: Optional[List[MarketplaceVersions]] = None


ID_DASHBOARD_DYNAMIC_MODEL = create_dynamic_model(
    # creating here with include_without_suffix == False
    field_name="id",
    type_=Optional[str],
    default=None,
)

StrictDashboard = create_model(
    model_name="StrictDashboard",
    base_models=(
        _StrictDashboard,
        BaseOptionalVersionJson,
        DESCRIPTION_DYNAMIC_MODEL,
        NAME_DYNAMIC_MODEL,
        ID_DASHBOARD_DYNAMIC_MODEL,
    ),
)
