from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    BaseStrictModel,
    create_model,
)


class _StrictAgentixSkill(BaseStrictModel):
    id_: str = Field(alias="id")
    name: str
    display: Optional[str] = None
    description: str
    content: Optional[str] = None
    internal: Optional[bool] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
    marketplaces: Optional[List[str]] = None


StrictAgentixSkill = create_model(
    model_name="StrictAgentixSkill",
    base_models=(
        _StrictAgentixSkill,
        BaseOptionalVersionJson,
    ),
)
