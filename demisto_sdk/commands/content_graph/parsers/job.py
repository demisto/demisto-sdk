from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class JobParser(JSONContentItemParser, content_type=ContentType.JOB):
    def __init__(self, path: Path, pack_marketplaces: List[MarketplaceVersions]) -> None:
        super().__init__(path, pack_marketplaces)

        self.connect_to_dependencies()

    @property
    def description(self) -> str:
        return self.json_data.get('details')

    def connect_to_dependencies(self) -> None:
        # todo: selectedFeeds - it's an *instances* list, not integrations!
        if playbook := self.json_data.get('playbookId'):
            self.add_dependency(playbook, ContentType.PLAYBOOK)
