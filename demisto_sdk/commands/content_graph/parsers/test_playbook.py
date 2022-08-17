
from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser


class TestPlaybookParser(PlaybookParser):
    def __init__(self, path: Path, pack_marketplaces: List[MarketplaceVersions]) -> None:
        super().__init__(path, pack_marketplaces)
        print(f'Parsing {self.content_type} {self.object_id}')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.TEST_PLAYBOOK
