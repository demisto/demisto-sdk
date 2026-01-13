from functools import cached_property
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.ai_prompt import AIPrompt


class AIPromptParser(YAMLContentItemParser, content_type=ContentType.AIPROMPT):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        pack_supported_modules: List[str],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(
            path, pack_marketplaces, pack_supported_modules, git_sha=git_sha
        )
        self.connect_to_dependencies()

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "object_id": "commonfields.id",
                "display": "name",
            }
        )
        return super().field_mapping

    @property
    def strict_object(self):
        return AIPrompt

    @property
    def user_prompt(self) -> str:
        return self.yml_data.get("userprompt", "")

    @property
    def system_prompt(self) -> Optional[str]:
        return self.yml_data.get("systemprompt")

    @property
    def model(self) -> Optional[str]:
        return self.yml_data.get("model")

    @property
    def pre_script(self) -> Optional[str]:
        return self.yml_data.get("prescript")

    @property
    def post_script(self) -> Optional[str]:
        return self.yml_data.get("postscript")

    @property
    def prompt_config(self) -> Optional[dict]:
        return self.yml_data.get("promptConfig")

    @property
    def arguments(self) -> Optional[list]:
        return self.yml_data.get("arguments")

    @property
    def private(self) -> bool:
        return self.yml_data.get("private", False)

    @property
    def source_script_id(self) -> Optional[str]:
        return self.yml_data.get("sourcescriptid")

    def connect_to_dependencies(self) -> None:
        """Create relationships to scripts used in pre/post processing.

        AIPrompts can reference scripts in their prescript and postscript fields.
        These are script IDs that should be executed before/after the LLM call.
        """
        # Connect to pre-script if specified
        if self.pre_script:
            self.add_dependency_by_id(
                self.pre_script, ContentType.SCRIPT, is_mandatory=True
            )

        # Connect to post-script if specified
        if self.post_script:
            self.add_dependency_by_id(
                self.post_script, ContentType.SCRIPT, is_mandatory=True
            )

        # Connect to source script if this was migrated from a Script
        if self.source_script_id:
            self.add_dependency_by_id(
                self.source_script_id, ContentType.SCRIPT, is_mandatory=False
            )