from pathlib import Path

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class TriggerParser(JSONContentItemParser, content_type=ContentTypes.TRIGGER):
    def __init__(self, path: Path) -> None:
        super().__init__(path)

        self.connect_to_dependencies()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.TRIGGER

    @property
    def object_id(self) -> str:
        return self.json_data.get('trigger_id')

    @property
    def name(self) -> str:
        return self.json_data.get('trigger_name')

    def connect_to_dependencies(self) -> None:
        if playbook := self.json_data.get('playbook_id'):
            self.add_dependency(playbook, ContentTypes.PLAYBOOK)
