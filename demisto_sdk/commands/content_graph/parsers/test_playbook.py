
from pathlib import Path
from typing import TYPE_CHECKING

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.parsers.pack import PackParser


class TestPlaybookParser(PlaybookParser):
    def __init__(self, path: Path, pack: 'PackParser') -> None:
        super().__init__(path, pack)
        print(f'Parsing {self.content_type} {self.object_id}')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.TEST_PLAYBOOK

    def add_to_pack(self) -> None:
        self.pack.content_items.test_playbook.append(self)
