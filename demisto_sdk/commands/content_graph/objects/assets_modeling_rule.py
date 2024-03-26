from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.modeling_rule import (
    ModelingRule,
)


class AssetsModelingRule(ModelingRule, content_type=ContentType.ASSETS_MODELING_RULE):  # type: ignore[call-arg]
    pass
