from typing import Optional, TypeVar

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
    FixingResult,
    ValidationResult,
)


class IDNameValidator(BaseValidator):
    error_code = "BA101"
    description = "Validate that the file id and name fields are identical."
    error_message = "The name attribute (currently {0}) should be identical to its `id` attribute ({1})"
    fixing_message = "Changing name to be equal to id ({0})."
    is_auto_fixable = True
    related_field = "name"
    ContentTypes = TypeVar("ContentTypes", Integration, Dashboard, IncidentType, Layout, Mapper, Playbook, Script, Wizard, Classifier)
    
    @classmethod
    def is_valid(cls, content_item: ContentTypes, old_content_item: Optional[ContentTypes] = None) -> ValidationResult:
        if content_item.object_id != content_item.name:
            return ValidationResult(
                error_code=cls.error_code,
                is_valid=False,
                message=cls.error_message.format(
                    content_item.object_id, content_item.name
                ),
                file_path=content_item.path,
            )
        return ValidationResult(
            error_code=cls.error_code,
            is_valid=True,
            message="",
            file_path=content_item.path,
        )
    @classmethod
    def fix(cls, content_item: ContentTypes) -> FixingResult:
        content_item.name = content_item.object_id
        content_item.save()
        return FixingResult(
            error_code=cls.error_code,
            message=cls.fixing_message.format(content_item.object_id),
            file_path=content_item.path,
        )
