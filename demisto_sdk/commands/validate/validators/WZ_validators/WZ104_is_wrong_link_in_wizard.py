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

    def integrations_without_playbook(self, content_item: ContentTypes) -> List[str]:
        content_item_json = json.loads(content_item.text)
        wizard_json_object = content_item_json.get('wizard', {})
        set_playbooks = wizard_json_object.get("set_playbook", [])
        playbooks_link_to_integration = {playbook.get("name", ""): playbook.get("link_to_integration") for playbook in
                                         set_playbooks}
        integrations = []
        for integration in wizard_json_object.get('fetching_integrations', []):
            integrations.append(integration.get('name'))

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
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                integrations_without_playbook := self.integrations_without_playbook(content_item)
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
