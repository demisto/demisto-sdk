
from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.content_item import IncorrectParserException
from demisto_sdk.commands.content_graph.parsers.script import ScriptParser
from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser


class TestPlaybookParser(PlaybookParser, content_type=ContentType.TEST_PLAYBOOK):
    def __init__(self, path: Path, pack_marketplaces: List[MarketplaceVersions]) -> None:
        """ Parses the test playbook.

        Args:
            path (Path): The test playbook's path.

        Raises:
            IncorrectParserException: When detecting this content item is a test script.
        """
        super().__init__(path, pack_marketplaces, is_test_playbook=True)

        if self.yml_data.get('script'):
            raise IncorrectParserException(correct_parser=ScriptParser, is_test_script=True)

