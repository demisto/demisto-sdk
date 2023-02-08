from pathlib import Path
from typing import List, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.content_item import (
    IncorrectParserException,
    NotAContentItemException,
)
from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser
from demisto_sdk.commands.content_graph.parsers.script import ScriptParser

NON_CIRCLE_TESTS_DIRECTORY = "NonCircleTests"


class TestPlaybookParser(PlaybookParser, content_type=ContentType.TEST_PLAYBOOK):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        """Parses the test playbook.

        Args:
            path (Path): The test playbook's path.

        Raises:
            NotAContentItemException: Indicating this test playbook should not be included in the graph.
            IncorrectParserException: When detecting this content item is a test script.
        """
        if NON_CIRCLE_TESTS_DIRECTORY in path.name:
            raise NotAContentItemException

        super().__init__(path, pack_marketplaces, is_test_playbook=True)

        if self.yml_data.get("script"):
            raise IncorrectParserException(
                correct_parser=ScriptParser, is_test_script=True
            )

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2}
