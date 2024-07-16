from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.base_script import BaseScriptParser
from demisto_sdk.commands.content_graph.strict_objects.script import StrictScript


class ScriptParser(BaseScriptParser, content_type=ContentType.SCRIPT):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(
            path=path,
            pack_marketplaces=pack_marketplaces,
            is_test_script=False,
            git_sha=git_sha,
        )

    @property
    def strict_object(self):
        return StrictScript
