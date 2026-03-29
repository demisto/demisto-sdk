from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StrictGenericIncidentType,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    BaseStrictModel,
    create_model,
)


class _StrictGenericType(BaseStrictModel):
    definition_id: str = Field(
        ...,
        alias="definitionId",
        description="ID of the generic object definition this type belongs to. Must reference a valid GenericDefinition ID.",
    )
    generic_module_id: str = Field(
        ...,
        alias="genericModuleId",
        description="ID of the generic module that contains this type. Must reference a valid GenericModule ID.",
    )


StrictGenericType = create_model(
    model_name="StrictGenericType",
    base_models=(_StrictGenericType, StrictGenericIncidentType),
)
