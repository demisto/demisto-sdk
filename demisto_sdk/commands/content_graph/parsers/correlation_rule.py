from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import YAMLContentItemParser


class CorrelationRuleParser(YAMLContentItemParser):
    @property
    def name(self) -> str:
        return self.yml_data['global_rule_id']

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.CORRELATION_RULE
