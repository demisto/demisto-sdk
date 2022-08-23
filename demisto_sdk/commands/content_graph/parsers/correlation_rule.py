from pathlib import Path

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import YAMLContentItemParser


class CorrelationRuleParser(YAMLContentItemParser, content_type=ContentTypes.CORRELATION_RULE):
    def __init__(self, path: Path) -> None:
        super().__init__(path)

    @property
    def object_id(self) -> str:
        return self.yml_data['global_rule_id']

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.CORRELATION_RULE
