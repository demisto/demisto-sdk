from functools import cached_property
from pathlib import Path
from typing import Dict, List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.base_script import EXECUTE_CMD_PATTERN
from demisto_sdk.commands.content_graph.parsers.integration_script import (
    IntegrationScriptParser,
)
from demisto_sdk.commands.content_graph.strict_objects.agentix_ai_task import (
    AgentixAITask,
)
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)


class AgentixAITaskParser(IntegrationScriptParser, content_type=ContentType.AGENTIX_AI_TASK):
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
        self.is_llm: bool = self.yml_data.get("isLLM")
        self.pre_script: str = self.yml_data.get("preScript")
        self.post_script: str = self.yml_data.get("postScript")
        self.user_prompt: str = self.yml_data.get("userPrompt")
        self.system_prompt: str = self.yml_data.get("systemPrompt")
        self.few_shots: str = self.yml_data.get("fewShots")

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "object_id": "id",
                "docker_image": "dockerimage",
                "description": "comment",
                "type": "type",
                "subtype": "subtype",
                "alt_docker_images": "alt_dockerimages",
                "outputs": "outputs",
            }
        )
        return super().field_mapping

    @property
    def strict_object(self):
        return AgentixAITask

    @property
    def outputs(self) -> List:
        return get_value(self.yml_data, self.field_mapping.get("outputs", ""), []) or []

    def connect_to_dependencies(self) -> None:
        """Creates USES_COMMAND_OR_SCRIPT mandatory relationships with the commands/scripts used.
        At this stage, we can't determine whether the dependencies are commands or scripts.
        """
        for cmd in self.get_depends_on():
            self.add_command_or_script_dependency(cmd)

        for cmd in self.get_command_executions():
            self.add_command_or_script_dependency(cmd)

    @property
    def args(self) -> List[Dict]:
        return self.yml_data.get("args", [])

    @property
    def runas(self) -> str:
        return self.yml_data.get("runas") or ""

    @property
    def code(self) -> Optional[str]:
        """Gets the script code.
        If the script is unified, it is taken from the yml file.
        Otherwise, uses the Unifier object to get it.

        Returns:
            str: The script code.
        """
        if self.is_unified or self.yml_data.get("script") not in ["-", ""]:
            return self.yml_data.get("script")
        if not self.git_sha:
            return IntegrationScriptUnifier.get_script_or_integration_package_data(
                self.path.parent
            )[1]
        else:
            return IntegrationScriptUnifier.get_script_or_integration_package_data_with_sha(
                self.path, self.git_sha, self.yml_data
            )[1]

    def get_depends_on(self) -> Set[str]:
        depends_on: List[str] = self.yml_data.get("dependson", {}).get("must", [])
        return {cmd.split("|")[-1] for cmd in depends_on}

    def get_command_executions(self) -> Set[str]:
        code = self.code
        if not code:
            raise ValueError("Script code is not available")
        return set(EXECUTE_CMD_PATTERN.findall(code))
