from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class WizardParser(JSONContentItemParser, content_type=ContentTypes.WIZARD):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.packs: List[str] = self.get_packs()
        self.integrations: List[str] = self.get_integrations()
        self.playbooks: List[str] = self.get_playbooks()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.WIZARD

    def get_packs(self) -> List[str]:
        packs: List[str] = []
        for packs_bundle in self.json_data.get('dependency_packs', []):
            for pack in packs_bundle.get('packs', []):
                packs.append(pack.get('name'))
        return packs

    def get_integrations(self) -> List[str]:
        integrations: List[str] = []
        for integration_type in ['fetching_integrations', 'supporting_integrations']:
            for integration in self.json_data.get('wizard', {}).get(integration_type, []):
                integrations.append(integration.get('name'))
        return integrations

    def get_playbooks(self) -> List[str]:
        playbooks: List[str] = []
        for playbook in self.json_data.get('wizard', {}).get('set_playbook', []):
            playbooks.append(playbook.get('name'))
        return playbooks
