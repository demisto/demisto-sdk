from pathlib import Path
from typing import Dict, List, Optional

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    FileType,
)
from TestSuite.json_based import JSONBased


class Wizard(JSONBased):
    def __init__(
        self,
        name: str,
        wizards_dir_path: Path,
        categories_to_packs: Optional[Dict[str, List[dict]]] = None,
        fetching_integrations: Optional[List[str]] = None,
        set_playbooks: Optional[List[dict]] = None,
        supporting_integrations: Optional[List[str]] = None,
    ):
        super().__init__(wizards_dir_path, name, "wizard")
        self.categories_to_packs = categories_to_packs or {}
        self.fetching_integrations = fetching_integrations or []
        self.set_playbooks = set_playbooks or []
        self.supporting_integrations = supporting_integrations or []

    def set_default_wizard_values(self):
        self.categories_to_packs = {
            "Endpoint Detection & Response": [
                {"name": "CrowdStrikeFalcon", "display_name": "CrowdStrike Falcon"},
                {
                    "name": "MicrosoftDefenderAdvancedThreatProtection",
                    "display_name": "Microsoft Defender for Endpoint",
                },
            ]
        }
        self.fetching_integrations = [
            "Microsoft Defender Advanced Threat Protection",
            "CrowdstrikeFalcon",
        ]
        self.supporting_integrations = ["WildFire-v2", "EWS Mail Sender"]
        self.set_playbooks = [
            {
                "name": "Endpoint Malware Investigation - Generic V2",
                "link_to_integration": "CrowdstrikeFalcon",
            },
            {
                "name": "Endpoint Malware Investigation - Generic V2",
                "link_to_integration": "Microsoft Defender Advanced Threat Protection",
            },
        ]
        return self

    def create_wizard(self):
        self.write_json(
            {
                "fromVersion": FILETYPE_TO_DEFAULT_FROMVERSION.get(FileType.WIZARD),
                "id": self.id,
                "name": self.id,
                "description": "description",
                "dependency_packs": self.create_dependency_packs(),
                "wizard": {
                    "fetching_integrations": self.create_integrations(
                        self.fetching_integrations
                    ),
                    "set_playbook": self.set_playbooks,
                    "supporting_integrations": self.create_integrations(
                        self.supporting_integrations
                    ),
                    "next": [
                        {
                            "name": "turn on use case",
                            "action": {
                                "existing": "something",
                                "new": "something else",
                            },
                        }
                    ],
                },
            }
        )

    def create_dependency_packs(self):
        return [
            {
                "name": category,
                "min_required": 1,
                "packs": [
                    {"name": pack["name"], "display_name": pack["display_name"]}
                    for pack in packs
                ],
            }
            for category, packs in self.categories_to_packs.items()
        ]

    @staticmethod
    def create_integrations(integrations: list) -> List[dict]:
        return [
            {
                "name": integration,
                "action": {"existing": "something", "new": "something else"},
                "description": "description",
            }
            for integration in integrations
        ]
