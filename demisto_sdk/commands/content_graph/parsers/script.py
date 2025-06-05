from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.parsers.base_script import BaseScriptParser
from demisto_sdk.commands.content_graph.strict_objects.script import StrictScript
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)


class ScriptParser(BaseScriptParser, content_type=ContentType.SCRIPT):
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
            is_test_script=False,
            git_sha=git_sha,
        )
        # self.is_llm: bool = self.yml_data.get("isLLM", False)
        self.model: str = self.yml_data.get("model", False)
        self.user_prompt: str = self.yml_data.get("userPrompt", '')
        self.system_prompt: str = self.yml_data.get("systemPrompt", '')
        self.few_shots: str = self.yml_data.get("fewShots", '')

    @property
    def strict_object(self):
        return StrictScript

    @property
    def is_llm(self) -> Optional[str]:
        return self.yml_data.get("isLLM", False)