from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StrictGenericIncidentType,
)


class StrictGenericType(StrictGenericIncidentType):  # type:ignore[valid-type,misc]
    definition_id: str = Field(..., alias="definitionId")
    generic_module_id: str = Field(..., alias="genericModuleId")
