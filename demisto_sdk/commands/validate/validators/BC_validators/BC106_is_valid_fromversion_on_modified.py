from __future__ import annotations

from typing import Iterable, List, Union, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.case_field import CaseField
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[
    Integration, Script, Mapper, IncidentType, IncidentField, CaseField
]


class IsValidFromversionOnModifiedValidator(BaseValidator[ContentTypes]):
    error_code = "BC106"
    description = (
        "Check that the fromversion property was not changed on existing Content files."
    )
    rationale = "Changing the `fromversion` for a content item can break backward compatibility. For 'fromversion' info, see: https://xsoar.pan.dev/docs/integrations/yaml-file#version-and-tests"
    error_message = "Changing the minimal supported version field `fromversion` is not allowed. Please undo, or request a force merge."
    related_field = "fromversion"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if fromversion_modified(content_item)
        ]


def fromversion_modified(content_item: ContentTypes) -> bool:
    if not content_item.old_base_content_object:
        return False
    old_file = cast(ContentTypes, content_item.old_base_content_object)
    return content_item.fromversion != old_file.fromversion
