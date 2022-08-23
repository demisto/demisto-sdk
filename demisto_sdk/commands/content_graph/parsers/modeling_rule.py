from pathlib import Path

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import YAMLContentItemParser


class ModelingRuleParser(YAMLContentItemParser, content_type=ContentTypes.MODELING_RULE):
    def __init__(self, path: Path) -> None:
        super().__init__(path)

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.MODELING_RULE

    @property
    def object_id(self) -> str:
        return self.yml_data.get('id')
