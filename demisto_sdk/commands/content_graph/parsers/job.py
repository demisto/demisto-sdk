from pathlib import Path
from typing import TYPE_CHECKING

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.parsers.pack import PackParser


class JobParser(JSONContentItemParser):
    def __init__(self, path: Path, pack: 'PackParser') -> None:
        super().__init__(path, pack)
        print(f'Parsing {self.content_type} {self.object_id}')

        self.connect_to_dependencies()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.JOB

    @property
    def description(self) -> str:
        return self.json_data.get('details')

    def connect_to_dependencies(self) -> None:
        # todo: selectedFeeds - it's an *instances* list, not integrations!
        if playbook := self.json_data.get('playbookId'):
            self.add_dependency(playbook, ContentTypes.PLAYBOOK)

    def add_to_pack(self) -> None:
        self.pack.content_items.job.append(self)
