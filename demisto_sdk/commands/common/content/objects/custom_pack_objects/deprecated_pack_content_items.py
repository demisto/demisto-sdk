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
        if deprecated_integrations := [integration for integration in self.integrations]:
            deprecated_content_items['integrations'] = deprecated_integrations
        if deprecated_playbooks := [playbook for playbook in self.playbooks]:
            deprecated_content_items['playbooks'] = deprecated_playbooks
        if deprecated_scripts := [script for script in self.scripts]:
            deprecated_content_items['scripts'] = deprecated_scripts
        return deprecated_content_items

    @property
    def deprecated_playbooks(self) -> List[Playbook]:
        """
        Returns all the deprecated playbooks in the pack.
        """
        return [playbook for playbook in self.playbooks if playbook.deprecated or playbook.hidden]

    @property
    def deprecated_integrations(self) -> List[Integration]:
        """
        Returns all the deprecated integrations in the pack.
        """
        return [integration for integration in self.integrations if integration.deprecated]

    @property
    def deprecated_scripts(self) -> List[Script]:
        """
        Returns all the deprecated scripts in the pack.
        """
        return [script for script in self.scripts if script.deprecated]

    @property
    def deprecated_playbooks_amount(self) -> int:
        """
        Amount of the deprecated playbooks in the pack.
        """
        return len(self.deprecated_playbooks)

    @property
    def deprecated_integrations_amount(self) -> int:
        """
        Amount of the deprecated integrations in the pack.
        """
        return len(self.deprecated_integrations)

    @property
    def deprecated_scripts_amount(self) -> int:
        """
        Amount of the deprecated scripts in the pack.
        """
        return len(self.deprecated_scripts)

    def should_pack_be_hidden(self) -> bool:
        """
        Determines if a pack should be hidden according to the following rules:

        1. if the pack is not already hidden.
        2. if all the content items (playbooks/scripts/integrations) are deprecated.

        Returns:
            bool: True if pack should be hidden according to the above, False if not.
        """
        if self.pack_metadata_as_dict.get('hidden', False):
            # pack is already hidden
            return False

        if self.integrations_amount or self.playbooks_amount or self.scripts_amount:
            return (
                self.integrations_amount == self.deprecated_integrations_amount
            ) and (
                self.playbooks_amount == self.deprecated_playbooks_amount
            ) and (
                self.scripts_amount == self.deprecated_scripts_amount
            )
        # if there aren't any playbooks/scripts/integrations -> no deprecated content -> pack shouldn't be hidden.
        return False
