from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.handlers import DEFAULT_JSON5_HANDLER as json
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Wizard


class IsWrongLinkInWizardValidator(BaseValidator[ContentTypes]):
    error_code = "WZ104"
    description = "Checks whether all fetching integrations are linked to a playbook."
    rationale = "Ensuring the wizard covers the use-case correctly with the relevant content items."
    error_message = "The following fetching integrations are not linked to a playbook: {0}"
    related_field = "wizard.fetching_integrations, wizard.set_playbooks"
    is_auto_fixable = False

    def integrations_without_playbook(self, content_item: ContentTypes) -> List[str]:
        content_item_json = json.loads(content_item.text)
        wizard_json_object = content_item_json.get("wizard", {})
        set_playbooks = wizard_json_object.get("set_playbook", [])
        playbooks_link_to_integration = {
            playbook.get("name", ""): playbook.get("link_to_integration")
            for playbook in set_playbooks
        }
        integrations = {integration.get("name") for integration in wizard_json_object.get("fetching_integrations", [])}

        integrations_without_playbook = []
        for link in playbooks_link_to_integration.values():
            if not link:  # handle case that a playbook was mapped to all integration
                break
            if link not in integrations:
                integrations_without_playbook.append(link)
            else:
                integrations.remove(link)

        return integrations_without_playbook

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    ", ".join(integrations_without_playbook)
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                integrations_without_playbook := self.integrations_without_playbook(
                    content_item
                )
            )
        ]
