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
    description = ""
    rationale = ""
    error_message = ""
    related_field = ""
    is_auto_fixable = False

    def exist_fetch_integrations_that_dont_have_playbook(self, content_item: ContentTypes) -> bool:
        wizard_json_object = json.loads(content_item.text)
        playbooks_link_to_integration = []
        for playbook in wizard_json_object.get('set_playbook', []):
            playbooks_link_to_integration.append(playbook.get('link_to_integration'))

        integrations = []
        for integration in wizard_json_object.get('fetching_integrations', []):
            integrations.append(integration.get('name'))
        for link in content_item.playbooks_link_to_integration:
            if not link:  # handle case that a playbook was mapped to all integration
                return False
            if link not in integrations:
                return True
            else:
                integrations.remove(link)

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                self.exist_fetch_integrations_that_dont_have_playbook(content_item)
            )
        ]

    # @error_codes("WZ104,WZ105")
    # def do_all_fetch_integrations_have_playbook(self):
    #     all_fetch_integrations_have_playbook = True
    #     integrations = self._fetching_integrations.copy()
    #     for link in self._set_playbooks.values():
    #         if not link:  # handle case that a playbook was mapped to all integration
    #             return True
    #         if link not in integrations:
    #             error_message, error_code = Errors.wrong_link_in_wizard(link)
    #             if self.handle_error(
    #                 error_message, error_code, file_path=self.file_path
    #             ):
    #                 all_fetch_integrations_have_playbook = False
    #         else:
    #             integrations.remove(link)
    #     if len(integrations) != 0:
    #         error_message, error_code = Errors.wizard_integrations_without_playbooks(
    #             integrations
    #         )
    #         if self.handle_error(error_message, error_code, file_path=self.file_path):
    #             all_fetch_integrations_have_playbook = False
    #     return all_fetch_integrations_have_playbook
