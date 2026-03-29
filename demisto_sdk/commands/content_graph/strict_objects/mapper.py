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
    id_: str = Field(
        ...,
        alias="id",
        description="Unique identifier of the mapper. Used internally to reference this mapper from integrations and classifiers.",
    )
    name: str = Field(
        ...,
        description="Unique display name of the mapper. Must be unique within the platform.",
    )
    type_: str = Field(
        ...,
        alias="type",
        description="Type of mapper. Must be 'mapping-incoming' for incoming mappers or 'mapping-outgoing' for outgoing mappers.",
    )
    description: str = Field(
        ...,
        description="Human-readable description of what this mapper does and which integrations or event sources it supports.",
    )
    version: int = Field(
        ...,
        description="Schema version of this mapper. Used for conflict detection. Typically -1 for new items.",
    )
    mapping: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="The mapping rules dictionary. Keys are incident type names, values are field mapping configurations.",
    )
    default_incident_type: Optional[str] = Field(
        None,
        alias="defaultIncidentType",
        description="Default incident type to use when no specific mapping rule matches. Must reference a valid incident type name.",
    )
    feed: Optional[bool] = Field(
        None,
        description="When True, this mapper is used for feed (indicator) incidents rather than regular incidents.",
    )
    definition_id: Optional[str] = Field(
        None,
        alias="definitionId",
        description="ID of the generic object definition this mapper is associated with. Used for generic object mappers.",
    )
    marketplaces: Optional[List[MarketplaceVersions]] = Field(
        None,
        description="Marketplace(s) this mapper is available in. Allowed values: xsoar, marketplacev2, xpanse, xsoar_saas, xsoar_on_prem, platform.",
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this mapper. Restricts availability to specific modules.",
    )


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
