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
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictWidget(BaseStrictModel):
    id_: str = Field(
        ...,
        alias="id",
        description="Unique identifier of the widget. Used internally to reference this widget from dashboards.",
    )
    version: int = Field(
        ...,
        description="Schema version of this widget. Used for conflict detection. Typically -1 for new items.",
    )
    name: str = Field(
        ...,
        description="Display name of the widget shown in the UI and on dashboards.",
    )
    description: str = Field(
        ...,
        description="Human-readable description of what data this widget displays and how to interpret it.",
    )
    data_type: Optional[str] = Field(
        None,
        alias="dataType",
        description="Type of data source for this widget (e.g. 'incidents', 'indicators', 'scripts'). Determines what data is queried.",
    )
    widget_type: str = Field(
        ...,
        alias="widgetType",
        description="Visual type of the widget. Must be one of: 'bar', 'column', 'pie', 'line', 'text', 'number', 'table', 'trend', 'duration', 'list'.",
    )
    query: Optional[str] = Field(
        None,
        description="Query string used to fetch data for this widget. Format depends on the dataType.",
    )
    is_predefined: bool = Field(
        ...,
        alias="isPredefined",
        description="When True, this is a system-provided widget that cannot be deleted.",
    )
    date_range: Optional[Dict[Any, Any]] = Field(
        None,
        alias="dateRange",
        description="Date range configuration for the widget's data query. Defines the time window for displayed data.",
    )
    params: Optional[Dict[Any, Any]] = Field(
        None,
        description="Additional parameters for the widget's data query and visualization configuration.",
    )
    size: Optional[int] = Field(
        None,
        description="Display size of the widget on the dashboard grid.",
    )
    sort: Optional[List[Any]] = Field(
        None,
        description="Sort configuration for the widget's data. Defines the order in which data is displayed.",
    )
    category: Optional[str] = Field(
        None,
        description="Category of the widget used for filtering in the widget library.",
    )
    modified: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp of when this widget was last modified. Set automatically by the platform.",
    )
    marketplaces: Optional[List[MarketplaceVersions]] = Field(
        None,
        enum=[
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
        ],
        description="Marketplace(s) this widget is available in. Restricted to XSOAR marketplaces: xsoar, xsoar_saas, xsoar_on_prem.",
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this widget. Restricts availability to specific modules.",
    )


StrictWidget = create_model(
    model_name="StrictWidget",
    base_models=(
        _StrictWidget,
        BaseOptionalVersionJson,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
