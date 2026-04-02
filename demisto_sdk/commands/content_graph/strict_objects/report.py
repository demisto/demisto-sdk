from typing import Any, Dict, List, Optional

from pydantic import Field, constr

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    ID_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class Period(BaseStrictModel):
    by_to: Optional[str] = Field(None, alias="byTo")
    by_from: Optional[str] = Field(None, alias="byFrom")
    to_value: Optional[int] = Field(None, alias="toValue")
    from_value: Optional[int] = Field(None, alias="fromValue")
    field: Optional[str] = None


class DateRange(BaseStrictModel):
    from_date: Optional[str] = Field(None, alias="fromDate")
    to_date: Optional[str] = Field(None, alias="toDate")
    from_date_license: Optional[str] = Field(None, alias="fromDateLicense")
    period: Optional[Period] = None


class _Widget(BaseStrictModel):
    size: Optional[int] = None
    data_type: Optional[str] = Field(None, alias="dataType")
    params: Optional[Any] = None
    query: Optional[str] = None
    modified: Optional[str] = None
    name: Optional[str] = None
    is_predefined: Optional[bool] = Field(None, alias="isPredefined")
    version: Optional[int] = None
    widget_type: Optional[str] = Field(None, alias="widgetType")
    date_range: Optional[DateRange] = Field(None, alias="dateRange")


Widget = create_model(
    model_name="Widget", base_models=(_Widget, NAME_DYNAMIC_MODEL, ID_DYNAMIC_MODEL)
)


class _Layout(BaseStrictModel):
    force_range: Optional[bool] = Field(None, alias="forceRange")
    x: Optional[int] = None
    y: Optional[int] = None
    i: Optional[str] = None
    w: Optional[int] = None
    h: Optional[int] = None
    widget: Optional[Widget] = None  # type:ignore[valid-type]


Layout = create_model(model_name="Layout", base_models=(_Layout, ID_DYNAMIC_MODEL))


class _Dashboard(BaseStrictModel):
    version: Optional[int] = None
    modified: Optional[str] = None
    from_date: Optional[str] = Field(None, alias="fromDate")
    to_date: Optional[str] = Field(None, alias="toDate")
    from_date_license: Optional[str] = Field(None, alias="fromDateLicense")
    name: Optional[str] = None
    is_predefined: Optional[bool] = Field(None, alias="isPredefined")
    period: Optional[Period]
    layout: Optional[List[Layout]] = None  # type:ignore[valid-type]


Dashboard = create_model(
    model_name="Dashboard",
    base_models=(_Dashboard, NAME_DYNAMIC_MODEL, ID_DYNAMIC_MODEL),
)


class _DecoderItem(BaseStrictModel):
    type: str = Field(enum=["string", "date", "duration", "image"])
    value: Optional[Any] = None
    description: Optional[str]


DecoderItem = create_model(
    model_name="DecoderItem", base_models=(_DecoderItem, DESCRIPTION_DYNAMIC_MODEL)
)


class _StrictReport(BaseStrictModel):
    id_: str = Field(alias="id")
    name: str
    description: str
    report_type: Optional[str] = Field(alias="reportType")
    tags: List[str]
    created_by: str = Field(alias="createdBy")
    latest_report_name: Optional[str] = Field(None, alias="latestReportName")
    modified: Optional[str] = None
    type_: str = Field(alias="type", enum=["pdf", "csv", "docx"])
    orientation: str = Field(enum=["landscape", "portrait", ""])
    recipients: List[str]
    system: Optional[bool] = None
    locked: Optional[bool] = None
    run_once: Optional[bool] = Field(None, alias="runOnce")
    times: Optional[int]
    start_date: Optional[str] = Field(None, alias="startDate")
    recurrent: Optional[bool] = None
    next_scheduled_time: Optional[str] = Field(None, alias="nextScheduledTime")
    ending_date: Optional[str] = Field(None, alias="endingDate")
    timezone_offset: Optional[int] = Field(None, alias="timezoneOffset")
    latest_scheduled_report_time: Optional[str] = Field(
        None, alias="latestScheduledReportTime"
    )
    latest_report_time: Optional[str] = Field(None, alias="latestReportTime")
    cron_view: Optional[bool] = Field(None, alias="cronView")
    scheduled: Optional[bool] = None
    running_user: Optional[str] = Field(None, alias="runningUser")
    paper_size: Optional[str] = Field(None, alias="paperSize")
    latest_report_username: Optional[str] = Field(None, alias="latestReportUsername")
    sensitive: Optional[bool] = None
    disable_header: Optional[bool] = Field(None, alias="disableHeader")
    dashboard: Optional[Dashboard] = None  # type:ignore[valid-type]
    decoder: Optional[Dict[constr(regex=r".+"), DecoderItem]] = None  # type:ignore[valid-type]
    sections: Any


StrictReport = create_model(
    model_name="StrictReport",
    base_models=(
        _StrictReport,
        BaseOptionalVersionJson,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        ID_DYNAMIC_MODEL,
    ),
)
