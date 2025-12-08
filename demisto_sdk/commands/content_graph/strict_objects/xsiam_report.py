from typing import Any, Dict, List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class LayoutData(BaseStrictModel):
    key: str
    data: Dict[Any, Any] = Field(default_factory=dict)


class _Layout(BaseStrictModel):
    id_: str = Field(alias="id")
    data: List[LayoutData]


Layout = create_model(
    model_name="Layout",
    base_models=(
        _Layout,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)


class TimeFrame(BaseStrictModel):
    relative_time: int = Field(alias="relativeTime")


class TemplatesData(BaseStrictModel):
    metadata: Optional[str] = None
    global_id: str
    report_name: str
    report_description: Optional[str] = None
    default_template_id: Optional[int] = None
    time_frame: Optional[TimeFrame] = None
    time_offset: int
    layout: List[Layout]  # type:ignore[valid-type]


class _WidgetsData(BaseStrictModel):
    widget_key: Optional[str] = None
    title: Optional[str] = None
    creation_time: Optional[int] = None
    description: Optional[str] = None
    data: dict = Field(default_factory=dict)
    support_time_range: Optional[bool] = None
    additional_info: dict = Field(default_factory=dict)


WidgetsData = create_model(
    model_name="WidgetsData",
    base_models=(
        _WidgetsData,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)


class _StrictXSIAMReport(BaseStrictModel):
    templates_data: List[TemplatesData]
    widgets_data: Optional[List[WidgetsData]] = None  # type:ignore[valid-type]


StrictXSIAMReport = create_model(
    model_name="StrictXSIAMReport",
    base_models=(
        _StrictXSIAMReport,
        BaseOptionalVersionJson,
    ),
)
