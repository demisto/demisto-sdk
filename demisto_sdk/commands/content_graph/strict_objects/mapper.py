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


class _StrictMapper(BaseStrictModel):
    id_: str = Field(alias="id")
    name: str
    type_: str = Field(alias="type")
    description: str
    version: int
    mapping: Optional[Dict[str, Any]] = Field(default_factory=dict)
    default_incident_type: Optional[str] = Field(None, alias="defaultIncidentType")
    feed: Optional[bool] = None
    definition_id: Optional[str] = Field(None, alias="definitionId")
    marketplaces: Optional[List[MarketplaceVersions]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")


StrictMapper = create_model(
    model_name="StrictMapper",
    base_models=(
        _StrictMapper,
        BaseOptionalVersionJson,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
