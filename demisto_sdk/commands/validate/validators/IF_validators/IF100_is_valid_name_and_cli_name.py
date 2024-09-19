from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.case_field import CaseField
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[CaseField, IncidentField]

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
    description = (
        "Checks if the name and cliName do not contain potential incident synonyms."
    )
    rationale = "The name and cliName fields are limited by the platform."
    error_message = "The following words cannot be used as a name: {words}."
    related_field = "name,cliName"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(words=", ".join(words)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                words := [
                    word.lower()
                    for word in content_item.name.split()
                    if word in BAD_WORDS
                ]
            )
        ]
