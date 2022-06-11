from typing import Dict, List

from demisto_sdk.commands.common.content.objects.pack_objects.integration.integration import \
    Integration
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.content.objects.pack_objects.playbook.playbook import \
    Playbook
from demisto_sdk.commands.common.content.objects.pack_objects.script.script import \
    Script


class DeprecatedPackContentItems(Pack):
    """
    A class which represents deprecated items of a single pack.
    """

    def get_deprecated_content_items_report(self) -> Dict:
        deprecated_content_items = {}
        if deprecated_integrations := self.deprecated_integrations:
            deprecated_content_items['integrations'] = deprecated_integrations
        if deprecated_playbooks := self.deprecated_playbooks:
            deprecated_content_items['playbooks'] = deprecated_playbooks
        if deprecated_scripts := self.deprecated_scripts:
            deprecated_content_items['scripts'] = deprecated_scripts
        return deprecated_content_items

    @property
    def deprecated_playbooks(self) -> List[Playbook]:
        return [playbook for playbook in self.playbooks if playbook.deprecated]

    @property
    def deprecated_integrations(self) -> List[Integration]:
        return [integration for integration in self.integrations if integration.deprecated]

    @property
    def deprecated_scripts(self) -> List[Script]:
        return [script for script in self.scripts if script.deprecated]

    def should_pack_be_hidden(self) -> bool:
        """
        Determines if a pack should be hidden according to the following rules:

        1. if the pack is not already hidden.
        2. If the pack has integrations and all integrations are deprecated -> pack should be hidden.
        3. if pack does not have integrations and all scripts and PBs are deprecated -> pack should be hidden.

        Returns:
            bool: True if pack should be hidden according to the above, False if not.
        """
        if self.pack_metadata_as_dict.get('hidden', False):
            # pack is already hidden
            return False

        pack_integrations_amount = self.integrations_amount
        if pack_integrations_amount > 0:
            # if there integrations and all of them are deprecated
            return pack_integrations_amount == len(self.deprecated_integrations)

        pack_scripts_amount = self.scripts_amount
        pack_playbooks_amount = self.playbooks_amount

        if pack_scripts_amount > 0 and pack_playbooks_amount > 0:
            return (
                pack_scripts_amount == len(self.deprecated_scripts)
            ) and (
                pack_playbooks_amount == len(self.deprecated_playbooks)
            )
        elif pack_scripts_amount > 0 and pack_playbooks_amount == 0:
            return pack_scripts_amount == len(self.deprecated_scripts)
        elif pack_scripts_amount == 0 and pack_playbooks_amount > 0:
            return pack_playbooks_amount == len(self.deprecated_playbooks)

        return False
