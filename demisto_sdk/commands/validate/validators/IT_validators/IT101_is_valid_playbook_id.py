from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    GitStatuses,
)
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IncidentType

# Checks if playbookID is a UUID format
INVALID_PLAYBOOK_ID = r"[\w\d]{8}-[\w\d]{4}-[\w\d]{4}-[\w\d]{4}-[\w\d]{12}"


class IncidentTypValidPlaybookIdValidator(BaseValidator[ContentTypes]):
    expected_git_statuses = [GitStatuses.ADDED]
    error_code = "IT101"
    rationale = "Playbook ID has to be a non-UUID format."
    description = "Checks if playbook ID is valid."
    error_message = (
        "The 'playbookId' field is not valid - please enter a non-UUID playbook ID."
    )
    related_field = "playbookId"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.data.get("playbookId")
                and re.search(
                    INVALID_PLAYBOOK_ID, content_item.data.get("playbookId", "")
                )
            )
        ]
