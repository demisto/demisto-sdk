from pathlib import Path
from typing import TYPE_CHECKING

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import YAMLContentItemParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.parsers.pack import PackParser


class ModelingRuleParser(YAMLContentItemParser):
    def __init__(self, path: Path, pack: 'PackParser') -> None:
        super().__init__(path, pack)
        print(f'Parsing {self.content_type} {self.object_id}')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.MODELING_RULE

    @property
    def object_id(self) -> str:
        return self.yml_data.get('id')

    def add_to_pack(self) -> None:
        self.pack.content_items.modeling_rule.append(self)
