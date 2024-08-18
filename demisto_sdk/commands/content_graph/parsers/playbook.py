from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.base_playbook import BasePlaybookParser

NON_CIRCLE_TESTS_DIRECTORY = "NonCircleTests"


class PlaybookParser(BasePlaybookParser, content_type=ContentType.PLAYBOOK):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        """Parses the test playbook.

        Args:
            path (Path): The test playbook's path.

        Raises:
            NotAContentItemException: Indicating this test playbook should not be included in the graph.
            IncorrectParserException: When detecting this content item is a test script.
        """
        super().__init__(
            path, pack_marketplaces, is_test_playbook=False, git_sha=git_sha
        )

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XPANSE,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
        }
