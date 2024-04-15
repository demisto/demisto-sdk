from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)

json = JSON_Handler()


class WizardParser(JSONContentItemParser, content_type=ContentType.WIZARD):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(path, pack_marketplaces, git_sha=git_sha)
        self.dependency_packs: str = json.dumps(
            self.json_data.get("dependency_packs") or []
        )
        self.packs: List[str] = self.get_packs()
        self.integrations: List[str] = self.get_integrations()
        self.playbooks: List[str] = self.get_playbooks()

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
        }

    def get_packs(self) -> List[str]:
        packs: List[str] = []
        for packs_bundle in self.json_data.get("dependency_packs", []):
            for pack in packs_bundle.get("packs", []):
                packs.append(pack.get("name"))
        return packs

    def get_integrations(self) -> List[str]:
        integrations: List[str] = []
        for integration_type in ["fetching_integrations", "supporting_integrations"]:
            for integration in self.json_data.get("wizard", {}).get(
                integration_type, []
            ):
                integrations.append(integration.get("name"))
        return integrations

    def get_playbooks(self) -> List[str]:
        playbooks: List[str] = []
        for playbook in self.json_data.get("wizard", {}).get("set_playbook", []):
            playbooks.append(playbook.get("name"))
        return playbooks
