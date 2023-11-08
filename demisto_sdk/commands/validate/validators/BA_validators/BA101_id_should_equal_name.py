from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[
    Integration,
    Dashboard,
    IncidentType,
    Layout,
    Mapper,
    Playbook,
    Script,
    Wizard,
    Classifier,
]


class IDNameValidator(BaseValidator[ContentTypes]):
    error_code = "BA101"
    description = "Validate that the file id and name fields are identical."
    error_message = "The name attribute (currently {0}) should be identical to its `id` attribute ({1})"
    fixing_message = "Changing name to be equal to id ({0})."
    related_field = "name"
    is_auto_fixable = True

    def is_valid(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.object_id, content_item.name
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.object_id != content_item.name
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.name = content_item.object_id
        return FixResult(
            validator=self,
            message=self.fixing_message.format(content_item.object_id),
            content_object=content_item,
        )
