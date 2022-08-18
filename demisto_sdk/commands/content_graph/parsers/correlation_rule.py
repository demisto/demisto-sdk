from pathlib import Path
from typing import TYPE_CHECKING

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import YAMLContentItemParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.parsers.pack import PackParser


class CorrelationRuleParser(YAMLContentItemParser):
    def __init__(self, path: Path, pack: 'PackParser') -> None:
        super().__init__(path, pack)
        print(f'Parsing {self.content_type} {self.object_id}')

    @property
    def name(self) -> str:
        return self.yml_data['global_rule_id']

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.CORRELATION_RULE

    def add_to_pack(self) -> None:
        self.pack.content_items.correlation_rule.append(self)
