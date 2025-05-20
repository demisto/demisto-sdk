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
    feed: Optional[bool] = None
    incident_samples: Optional[List[str]] = Field(None, alias="incidentSamples")
    indicator_samples: Optional[List[str]] = Field(None, alias="indicatorSamples")
    propagation_labels: Optional[Any] = Field(None, alias="propagationLabels")
    is_default: Optional[bool] = Field(None, alias="isDefault")
    sort_values: Optional[Any] = Field(None, alias="sortValues")
    modified: Optional[str] = None
    default_incident_type: Optional[str] = Field(None, alias="defaultIncidentType")
    unclassified_cases: Optional[dict] = Field(None, alias="unclassifiedCases")
    transformer: Optional[dict] = None
    key_type_map: Optional[dict] = Field(None, alias="keyTypeMap")
    custom: Optional[bool] = None
    name: str
    type_: str = Field(..., alias="type")
    description: str
    definition_id: Optional[str] = Field(None, alias="definitionId")
    marketplaces: Optional[List[MarketplaceVersions]] = Field(
        None, alias="marketplaces"
    )
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
    id_: str = Field(..., alias="id")
    version: int


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
