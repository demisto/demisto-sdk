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

    @property
    def pre_script(self) -> Optional[str]:
        return self.get_code_by_key(key="preScript")

    @property
    def post_script(self) -> Optional[str]:
        return self.get_code_by_key(key="postScript")

    def connect_to_dependencies(self) -> None:
        """Creates USES_COMMAND_OR_SCRIPT mandatory relationships with the commands/scripts used.
        At this stage, we can't determine whether the dependencies are commands or scripts.
        """
        if not self.is_llm:
            super().connect_to_dependencies()
        else:
            for cmd in self.get_depends_on():
                self.add_command_or_script_dependency(cmd)
            for code in [self.code, self.pre_script, self.post_script]:
                if code:
                    for cmd in self.get_command_executions(code):
                        self.add_command_or_script_dependency(cmd)

    def connect_to_api_modules(self) -> None:
        """Creates IMPORTS relationships with the API modules used in the integration."""
        if not self.is_llm:
            super().connect_to_api_modules()
        if pre_script:=self.pre_script:
            api_modules = IntegrationScriptUnifier.check_api_module_imports(pre_script).values()
            for api_module in api_modules:
                self.add_relationship(
                    RelationshipType.IMPORTS, api_module, ContentType.SCRIPT
                )
        if post_script:=self.post_script:
            api_modules = IntegrationScriptUnifier.check_api_module_imports(post_script).values()
            for api_module in api_modules:
                self.add_relationship(
                    RelationshipType.IMPORTS, api_module, ContentType.SCRIPT
                )