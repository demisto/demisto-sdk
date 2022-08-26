
from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import IncorrectParser
from demisto_sdk.commands.content_graph.parsers.script import ScriptParser
from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser


class TestPlaybookParser(PlaybookParser, content_type=ContentTypes.TEST_PLAYBOOK):
    def __init__(self, path: Path) -> None:
        """ Parses the test playbook.

        Args:
            path (Path): The test playbook's path.

        Raises:
            IncorrectParser: When detecting this content item is a test script.
        """
        super().__init__(path, is_test=True)

        if self.yml_data.get('script'):
            raise IncorrectParser(correct_parser=ScriptParser, is_test=True)

