from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.base_script import BaseScriptParser
from demisto_sdk.commands.content_graph.strict_objects.script import StrictScript


class TestScriptParser(BaseScriptParser, content_type=ContentType.TEST_SCRIPT):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        pack_supported_modules: List[str],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(
            path=path,
            pack_marketplaces=pack_marketplaces,
            pack_supported_modules=pack_supported_modules,
            is_test_script=True,
            git_sha=git_sha,
        )

    @property
    def strict_object(self):
        return StrictScript
