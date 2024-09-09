from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.modeling_rule import ModelingRuleParser
from demisto_sdk.commands.content_graph.strict_objects.assets_modeling_rule import (
    StrictAssetsModelingRule,
)


class AssetsModelingRuleParser(
    ModelingRuleParser, content_type=ContentType.ASSETS_MODELING_RULE
):
    @property
    def description(self) -> str:
        return "Collect assets and vulnerabilities"

    @property
    def strict_object(self):
        return StrictAssetsModelingRule
