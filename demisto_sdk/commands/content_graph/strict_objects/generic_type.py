from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StrictGenericIncidentType,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    SupportedFeaturesMixin,
    create_model,
)


class _StrictGenericType(SupportedFeaturesMixin):
    definition_id: str = Field(..., alias="definitionId")
    generic_module_id: str = Field(..., alias="genericModuleId")


StrictGenericType = create_model(
    model_name="StrictGenericType",
    base_models=(_StrictGenericType, StrictGenericIncidentType),
)
