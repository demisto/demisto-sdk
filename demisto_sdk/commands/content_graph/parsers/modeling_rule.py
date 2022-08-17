from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import YAMLContentItemParser


class ModelingRuleParser(YAMLContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[MarketplaceVersions]) -> None:
        super().__init__(path, pack_marketplaces)
        print(f'Parsing {self.content_type} {self.object_id}')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.MODELING_RULE

    @property
    def object_id(self) -> str:
        return self.yml_data.get('id')
