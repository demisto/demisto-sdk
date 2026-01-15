from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.ai_prompt import (
    AIPrompt,
)


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
        # Core prompt fields
        self.user_prompt: str = self.yml_data.get("userprompt", "")
        self.system_prompt: Optional[str] = self.yml_data.get("systemprompt")
        self.few_shots: Optional[str] = self.yml_data.get("fewshots")
        self.pre_script: Optional[str] = self.yml_data.get("prescript")
        self.post_script: Optional[str] = self.yml_data.get("postscript")
        self.prompt_config: Optional[dict] = self.yml_data.get("promptConfig")

        # Arguments and outputs
        self.arguments: Optional[list] = self.yml_data.get("arguments")
        self.outputs: Optional[list] = self.yml_data.get("outputs")

        # Metadata fields
        self.tags: Optional[List[str]] = self.yml_data.get("tags")
        self.pretty_name: Optional[str] = self.yml_data.get("prettyname")
        self.comment: Optional[str] = self.yml_data.get("comment")

        # Boolean flags
        self.private: bool = self.yml_data.get("private", False)
        self.is_internal: bool = self.yml_data.get("isInternal", False)
        self.is_anonymous: bool = self.yml_data.get("isanonymous", False)
        self.enabled: bool = self.yml_data.get("enabled", True)
        self.system: bool = self.yml_data.get("system", False)
        self.locked: bool = self.yml_data.get("locked", False)
        self.sensitive: bool = self.yml_data.get("sensitive", False)
        self.hidden: bool = self.yml_data.get("hidden", False)

        # Execution settings
        self.run_as: Optional[str] = self.yml_data.get("runas")
        self.timeout: Optional[str] = self.yml_data.get("timeout")
        self.password: Optional[str] = self.yml_data.get("pswd")
        self.compliant_policies: Optional[List[str]] = self.yml_data.get(
            "compliantpolicies"
        )

        self.connect_to_dependencies()

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "object_id": "commonfields.id",
                "version": "commonfields.version",
                "display": "name",
            }
        )
        return super().field_mapping

    @property
    def strict_object(self):
        return AIPrompt

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.PLATFORM}

    def connect_to_dependencies(self) -> None:
        """Create relationships to scripts used in pre/post processing.

        AIPrompts can reference scripts in their prescript and postscript
        fields. These are script IDs executed before/after the LLM call.
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
