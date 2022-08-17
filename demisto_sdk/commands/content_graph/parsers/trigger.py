from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class TriggerParser(JSONContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        super().__init__(path, pack_marketplaces)
        self.description = self.json_data.get('description')
        self.object_id = self.json_data.get('trigger_id')
        self.name = self.json_data.get('trigger_name')

        self.connect_to_dependencies()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.TRIGGER

    def connect_to_dependencies(self) -> None:
        if playbook := self.json_data.get('playbook_id'):
            self.add_dependency(playbook, ContentTypes.PLAYBOOK)
