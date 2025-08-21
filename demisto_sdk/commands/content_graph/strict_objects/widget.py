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
    id_: str = Field(alias="id")
    version: int
    name: str
    description: str
    data_type: Optional[str] = Field(None, alias="dataType")
    widget_type: str = Field(alias="widgetType")
    query: Optional[str] = None
    is_predefined: bool = Field(alias="isPredefined")
    date_range: Optional[Dict[Any, Any]] = Field(None, alias="dateRange")
    params: Optional[Dict[Any, Any]] = None
    size: Optional[int] = None
    sort: Optional[List[Any]] = None
    category: Optional[str] = None
    modified: Optional[str] = None
    marketplaces: Optional[List[MarketplaceVersions]] = Field(
        None,
        enum=[
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
        ],
    )
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")


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
