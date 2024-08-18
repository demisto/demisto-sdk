from __future__ import annotations

from typing import Iterable, List

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    GitStatuses,
)
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

FIELDS_TO_INCLUDE = ["hours", "days", "weeks", "hoursR", "daysR", "weeksR"]
ContentTypes = IncidentType


class IncidentTypeIncludesIntFieldValidator(BaseValidator[ContentTypes]):
    expected_git_statuses = [GitStatuses.ADDED]
    error_code = "IT100"
    rationale = "Fields that have to be included, cannot be of type integer."
    description = "Checks if the included fields have a positive integer value."
    error_message = (
        "The '{0}' fields need to be included with a positive integer. "
        "Please add them with positive integer value."
    )
    related_field = ""

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_fields)),
                content_object=content_item,
            )
            for content_item in content_items
            if (invalid_fields := self.fields_to_include(content_item))
        ]

    @staticmethod
    def fields_to_include(incident_type: ContentTypes):
        fields = []
        from_version = incident_type.fromversion or DEFAULT_CONTENT_ITEM_FROM_VERSION

        if Version(from_version) >= Version("5.0.0"):
            for field in FIELDS_TO_INCLUDE:
                int_field = incident_type.data_dict.get(field, -1)
                if not isinstance(int_field, int) or int_field < 0:
                    fields.append(field)
        return fields
