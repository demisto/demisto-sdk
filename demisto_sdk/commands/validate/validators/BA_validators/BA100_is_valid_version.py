from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.generic_definition import (
    GenericDefinition,
)
from demisto_sdk.commands.content_graph.objects.generic_field import GenericField
from demisto_sdk.commands.content_graph.objects.generic_module import GenericModule
from demisto_sdk.commands.content_graph.objects.generic_type import GenericType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.list import List as List_Obj
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[
    Integration,
    Script,
    Playbook,
    Dashboard,
    Classifier,
    IncidentType,
    Layout,
    Mapper,
    Wizard,
    IncidentField,
    IndicatorField,
    IndicatorType,
    TestPlaybook,
    GenericDefinition,
    GenericField,
    GenericModule,
    GenericType,
    List_Obj,
    Widget,
]


class IsValidVersionValidator(BaseValidator[ContentTypes]):
    error_code = "BA100"
    description = "Marketplace content set to -1 makes it easier to tell from modified, versioned content."
    rationale = (
        "The version for system content items should always be -1 as per the standard."
    )
    error_message = (
        "The version for our files should always be -1, please update the file."
    )
    fix_message = "Updated the content item version to -1."
    related_field = "version, commonfields.version"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.version != -1
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.version = -1
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
