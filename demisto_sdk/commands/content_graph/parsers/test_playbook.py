
from pathlib import Path

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import IncorrectParser
from demisto_sdk.commands.content_graph.parsers.script import ScriptParser
from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser


class TestPlaybookParser(PlaybookParser, content_type=ContentTypes.TEST_PLAYBOOK):
    def __init__(self, path: Path) -> None:
        super().__init__(path)

        if self.yml_data.get('script'):
            raise IncorrectParser(correct_parser=ScriptParser)

        print(f'Parsing {self.content_type} {self.object_id}')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.TEST_PLAYBOOK
