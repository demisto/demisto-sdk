from typing import Any, Dict, List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    ID_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class DashboardWidget(BaseStrictModel):
    cache: Optional[str] = Field(None, alias="Cache")
    cache_versn: Optional[int] = Field(None, alias="cacheVersn")
    category: Optional[str] = None
    created: Optional[str] = None
    data_type: Optional[str] = Field(None, alias="dataType")
    date_range: Optional[Dict[str, Any]] = Field(
        alias="dateRange", default_factory=dict
    )
    definition_id: Optional[str] = Field(None, alias="definitionId")
    from_server_version: Optional[str] = Field(None, alias="fromServerVersion")
    id_: Optional[str] = Field(None, alias="id")
    index_name: Optional[str] = Field(None, alias="indexName")
    is_predefined: Optional[bool] = Field(None, alias="isPredefined")
    item_version: Optional[str] = Field(None, alias="itemVersion")
    modified: Optional[str] = None
    name: Optional[str] = None
    pack_id: Optional[str] = Field(None, alias="packID")
    pack_name: Optional[str] = Field(None, alias="packName")
    pack_propagation_labels: Optional[List[str]] = Field(
        None, alias="packPropagationLabels"
    )
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)
    prev_name: Optional[str] = Field(None, alias="prevName")
    primary_term: Optional[int] = Field(None, alias="primaryTerm")
    propagation_labels: Optional[List[str]] = Field(None, alias="propagationLabels")
    query: Optional[str] = None
    sequence_number: Optional[int] = Field(None, alias="sequenceNumber")
    size_in_bytes: Optional[int] = Field(None, alias="sizeInBytes")
    to_server_version: Optional[str] = Field(None, alias="toServerVersion")
    vc_should_keep_item_legacy_prod_machine: Optional[str] = Field(
        None, alias="vcShouldKeepItemLegacyProdMachine"
    )
    version: Optional[int] = None
    widget_type: Optional[str] = Field(None, alias="widgetType")
    commit_message: Optional[str] = Field(None, alias="commitMessage")
    should_commit: Optional[bool] = Field(None, alias="shouldCommit")
    size: Optional[int] = None
    sort: Optional[Any] = None
    sort_values: Optional[Any] = Field(None, alias="sortValues")
    vc_should_ignore: Optional[bool] = Field(None, alias="vcShouldIgnore")
    description: Optional[str] = None
    from_version: Optional[str] = Field(None, alias="fromVersion")
    locked: Optional[bool] = None


class _DashboardLayout(BaseStrictModel):
    force_range: bool = Field(alias="forceRange")
    x: int
    y: int
    h: int
    w: int
    i: str
    widget: DashboardWidget = Field(default_factory=dict)
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
    period: Optional[Dict[str, Any]] = Field(default_factory=dict)
    layout: Optional[List[DashboardLayout]] = Field(default_factory=list)  # type:ignore[valid-type]
    marketplaces: Optional[List[MarketplaceVersions]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")


StrictDashboard = create_model(
    model_name="StrictDashboard",
    base_models=(
        _StrictDashboard,
        BaseOptionalVersionJson,
        DESCRIPTION_DYNAMIC_MODEL,
        NAME_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
