from typing import Any, List, Optional

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
    BaseStrictModel,
    create_model,
)


class _StrictClassifier(BaseStrictModel):
    feed: Optional[bool] = Field(
        None,
        description="When True, this classifier is used for feed (indicator) incidents rather than regular incidents.",
    )
    incident_samples: Optional[List[str]] = Field(
        None,
        alias="incidentSamples",
        description="List of sample incident JSON strings used to test and preview the classifier mapping.",
    )
    indicator_samples: Optional[List[str]] = Field(
        None,
        alias="indicatorSamples",
        description="List of sample indicator JSON strings used to test and preview the classifier mapping for feed classifiers.",
    )
    propagation_labels: Optional[Any] = Field(
        None,
        alias="propagationLabels",
        description="Labels used for data propagation in multi-tenant environments. Controls which tenants receive classified incidents.",
    )
    is_default: Optional[bool] = Field(
        None,
        alias="isDefault",
        description="When True, this classifier is the default classifier applied to incidents that do not match any other classifier.",
    )
    sort_values: Optional[Any] = Field(
        None,
        alias="sortValues",
        description="Internal field used for sorting classifiers in the UI. Not typically set manually.",
    )
    modified: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp of when this classifier was last modified. Set automatically by the platform.",
    )
    default_incident_type: Optional[str] = Field(
        None,
        alias="defaultIncidentType",
        description="Default incident type to assign when no mapping rule matches. Must reference a valid incident type name.",
    )
    unclassified_cases: Optional[dict] = Field(
        None,
        alias="unclassifiedCases",
        description="Mapping of unclassified event keys to incident types. Used as a fallback when the main keyTypeMap has no match.",
    )
    transformer: Optional[dict] = Field(
        None,
        description="Transformation rules applied to incoming event data before classification. Supports complex field extraction and manipulation.",
    )
    key_type_map: Optional[dict] = Field(
        None,
        alias="keyTypeMap",
        description="Mapping from event field values to incident types. The classifier uses this map to determine the incident type for each incoming event.",
    )
    custom: Optional[bool] = Field(
        None,
        description="When True, marks this as a custom (user-created) classifier rather than a system-provided one.",
    )
    name: str = Field(
        ...,
        description="Unique display name of the classifier. Must be unique within the platform.",
    )
    type_: str = Field(
        ...,
        alias="type",
        description="Type of classifier. Must be 'classification' for incident classifiers or 'mapping' for mapper-type classifiers.",
    )
    description: str = Field(
        ...,
        description="Human-readable description of what this classifier does and which integrations or event sources it supports.",
    )
    definition_id: Optional[str] = Field(
        None,
        alias="definitionId",
        description="ID of the generic object definition this classifier is associated with. Used for generic object classifiers.",
    )
    marketplaces: Optional[List[MarketplaceVersions]] = Field(
        None,
        alias="marketplaces",
        description="Marketplace(s) this classifier is available in. Allowed values: xsoar, marketplacev2, xpanse, xsoar_saas, xsoar_on_prem, platform.",
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this classifier. Restricts availability to specific modules.",
    )
    id_: str = Field(
        ...,
        alias="id",
        description="Unique identifier of the classifier. Used internally to reference this classifier from integrations and other content items.",
    )
    version: int = Field(
        ...,
        description="Schema version of this classifier. Used for conflict detection and migration. Typically -1 for new items.",
    )


StrictClassifier = create_model(
    model_name="StrictClassifier",
    base_models=(
        _StrictClassifier,
        NAME_DYNAMIC_MODEL,
        ID_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        BaseOptionalVersionJson,
    ),
)
