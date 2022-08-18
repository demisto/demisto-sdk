from pathlib import Path
from typing import TYPE_CHECKING

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.parsers.pack import PackParser


class TriggerParser(JSONContentItemParser):
    def __init__(self, path: Path, pack: 'PackParser') -> None:
        super().__init__(path, pack)
        print(f'Parsing {self.content_type} {self.object_id}')

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

    def add_to_pack(self) -> None:
        self.pack.content_items.trigger.append(self)
