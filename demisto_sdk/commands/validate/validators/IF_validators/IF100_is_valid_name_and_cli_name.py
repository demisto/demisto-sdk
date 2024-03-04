from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import RelatedFileType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IncidentField

BAD_WORDS = {
    "incident",
    "case",
    "alert",
    "event",
    "playbook",
    "ticket",
    "issue",
    "incidents",
    "cases",
    "alerts",
    "events",
    "playbooks",
    "tickets",
    "issues",
}


class IsValidNameAndCliNameValidator(BaseValidator[ContentTypes]):
    error_code = "IF100"
    description = "Validate that the name and cliName does not contain any potential incident synonyms."
    error_message = (
        "The words: {words} cannot be used as a name.\n"
        "To fix the problem, remove the words {words}, "
        "or add them to the whitelist named argsExceptionsList in:\n"
        "https://github.com/demisto/server/blob/57fbe417ae420c41ee12a9beb850ff4672209af8/services/servicemodule_test.go#L8273"
    )
    related_field = "name,cliName"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.JSON]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(words=", ".join(words)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                words := [
                    word for word in content_item.name.split() if word in BAD_WORDS
                ]
            )
        ]
