from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictXDRCTemplate(BaseStrictModel):
    os_type: str
    profile_type: str
    name: str
    content_global_id: str
    from_xdr_version: str
    yaml_template: str


StrictXDRCTemplate = create_model(
    model_name="StrictXDRCTemplate",
    base_models=(
        _StrictXDRCTemplate,
        BaseOptionalVersionJson,
        NAME_DYNAMIC_MODEL,
    ),
)
