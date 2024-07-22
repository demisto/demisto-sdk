from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StrictBaseClassifier,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    ID_DYNAMIC_MODEL,
    create_model,
)


class _StrictClassifier599(StrictBaseClassifier):
    brand_name: str = Field(..., alias="brandName")


StrictClassifier599 = create_model(
    model_name="StrictClassifier599",
    base_models=(
        _StrictClassifier599,
        ID_DYNAMIC_MODEL,
    ),
)
