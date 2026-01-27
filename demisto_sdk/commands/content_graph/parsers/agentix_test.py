from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import (
    DEFAULT_AGENTIX_ITEM_FROM_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.agentix_test import (
    AgentixTestFile,
)


class AgentixTestParser(YAMLContentItemParser, content_type=ContentType.AGENTIX_TEST):
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

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.PLATFORM}

    @property
    def strict_object(self):
        return AgentixTestFile

    @property
    def object_id(self) -> Optional[str]:
        return self.yml_data.get("id") or self.path.stem

    @property
    def name(self) -> Optional[str]:
        return self.yml_data.get("name") or self.path.stem

    @property
    def display_name(self) -> Optional[str]:
        return self.name

    @property
    def fromversion(self) -> str:
        return self.yml_data.get("fromversion") or DEFAULT_AGENTIX_ITEM_FROM_VERSION

    @property
    def tests(self) -> List[dict]:
        return self.yml_data.get("tests", [])

    def connect_to_dependencies(self) -> None:
        """Create USES relationship to the agents used in the tests."""
        for test in self.tests:
            if agent_id := test.get("agent_id"):
                self.add_dependency_by_id(
                    agent_id, ContentType.AGENTIX_AGENT, is_mandatory=True
                )
            for outcome in test.get("expected_outcomes", []):
                for action in outcome.get("actions", []):
                    if action_id := action.get("action_id"):
                        self.add_dependency_by_id(
                            action_id, ContentType.AGENTIX_ACTION, is_mandatory=True
                        )
