from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StrictBaseClassifier,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    ID_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    create_model,
)


class _StrictClassifier(StrictBaseClassifier):
    name: str
    type_: str = Field(..., alias="type")
    description: str
    definition_id: Optional[str] = Field(None, alias="definitionId")
    marketplaces: Optional[List[MarketplaceVersions]] = Field(
        None, alias="marketplaces"
    )


StrictClassifier = create_model(
    model_name="StrictClassifier",
    base_models=(
        _StrictClassifier,
        NAME_DYNAMIC_MODEL,
        ID_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)
