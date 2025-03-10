from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.base_playbook import BasePlaybookParser
from demisto_sdk.commands.content_graph.parsers.content_item import (
    IncorrectParserException,
    NotAContentItemException,
)
from demisto_sdk.commands.content_graph.parsers.test_script import TestScriptParser

NON_CIRCLE_TESTS_DIRECTORY = "NonCircleTests"


class TestPlaybookParser(BasePlaybookParser, content_type=ContentType.TEST_PLAYBOOK):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        pack_supported_modules: List[str],
        git_sha: Optional[str] = None,
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

        super().__init__(
            path,
            pack_marketplaces,
            pack_supported_modules,
            is_test_playbook=True,
            git_sha=git_sha,
        )

        if self.yml_data.get("script"):
            raise IncorrectParserException(correct_parser=TestScriptParser)

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
            MarketplaceVersions.PLATFORM,
        }
