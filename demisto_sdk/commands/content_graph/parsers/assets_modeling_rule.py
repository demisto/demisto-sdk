from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.modeling_rule import ModelingRuleParser


class AssetsModelingRuleParser(
    ModelingRuleParser, content_type=ContentType.ASSETS_MODELING_RULE
):
    @property
    def description(self) -> str:
        return "Collect assets and vulnerabilities"
