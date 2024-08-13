from typing import Any, Dict, List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class LayoutData(BaseStrictModel):
    key: str
    data: Dict[Any, Any] = Field(default_factory=dict)


class _Layout(BaseStrictModel):
    id: str
    data: List[LayoutData]


Layout = create_model(
    model_name="Layout",
    base_models=(
        _Layout,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)


class _DashboardsData(BaseStrictModel):
    global_id: str
    status: str
    name: str
    description: Optional[str] = None
    default_dashboard_id: int
    layout: List[Layout]  # type:ignore[valid-type]
    metadata: Optional[Dict[Any, Any]] = Field(default_factory=dict)


DashboardsData = create_model(
    model_name="DashboardsData",
    base_models=(
        _DashboardsData,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)


class _WidgetsData(BaseStrictModel):
    widget_key: str
    title: str
    creation_time: int
    description: str
    data: Dict[Any, Any] = Field(default_factory=dict)
    support_time_range: bool
    additional_info: Dict[Any, Any] = Field(default_factory=dict)


WidgetsData = create_model(
    model_name="WidgetsData",
    base_models=(
        _WidgetsData,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)


class Metadata(BaseStrictModel):
    lazy_load: Optional[bool] = None
    cache_ttl: Optional[int] = None


class _StrictXSIAMDashboard(BaseStrictModel):
    dashboards_data: List[DashboardsData]  # type:ignore[valid-type]
    widgets_data: List[WidgetsData]  # type:ignore[valid-type]
    metadata: Optional[Metadata] = None


StrictXSIAMDashboard = create_model(
    model_name="StrictXSIAMDashboard",
    base_models=(
        _StrictXSIAMDashboard,
        BaseOptionalVersionJson,
    ),
)
