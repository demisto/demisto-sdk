from typing import Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StrictGenericIncidentType,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    BaseStrictModel,
    SupportedFeaturesList,
    create_model,
)


class _StrictGenericType(BaseStrictModel):
    supportedFeatures: Optional[SupportedFeaturesList] = Field(
        None, alias="supportedFeatures"
    )
    definition_id: str = Field(..., alias="definitionId")
    generic_module_id: str = Field(..., alias="genericModuleId")


StrictGenericType = create_model(
    model_name="StrictGenericType",
    base_models=(_StrictGenericType, StrictGenericIncidentType),
)
