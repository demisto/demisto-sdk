from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import YAMLContentItemParser


class ModelingRuleParser(YAMLContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        super().__init__(path, pack_marketplaces)
        self.description = self.yml_data.get('description')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.MODELING_RULE

    @property
    def object_id(self) -> str:
        return self.yml_data.get('id')
