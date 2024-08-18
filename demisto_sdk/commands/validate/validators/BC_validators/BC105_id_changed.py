from __future__ import annotations

from typing import Dict, Iterable, List, Union, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.case_field import CaseField
from demisto_sdk.commands.content_graph.objects.case_layout import CaseLayout
from demisto_sdk.commands.content_graph.objects.case_layout_rule import CaseLayoutRule
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
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
from demisto_sdk.commands.content_graph.objects.job import Job
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.layout_rule import LayoutRule
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.report import Report
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[
    Integration,
    Script,
    Playbook,
    Pack,
    Dashboard,
    Classifier,
    Job,
    Layout,
    Mapper,
    Wizard,
    CorrelationRule,
    IncidentField,
    IncidentType,
    IndicatorField,
    IndicatorType,
    LayoutRule,
    Layout,
    ModelingRule,
    ParsingRule,
    Report,
    TestPlaybook,
    Trigger,
    Widget,
    GenericDefinition,
    GenericField,
    GenericModule,
    GenericType,
    XSIAMDashboard,
    XSIAMReport,
    CaseField,
    CaseLayout,
    CaseLayoutRule,
]


class IdChangedValidator(BaseValidator[ContentTypes]):
    error_code = "BC105"
    description = "Validate that the ID of the content item was not changed."
    error_message = "ID of content item was changed from {0} to {1}, please undo."
    rationale = (
        "Changing the ID of an item will cause it to show as a new item in the platform, "
        "and not update properly for users who already have a previous version installed."
    )
    fix_message = "Changing ID back to {0}."
    related_field = "id"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]
    is_auto_fixable = True
    old_id: Dict[str, str] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    self.old_id[content_item.name],
                    content_item.object_id,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if self.id_has_changed(content_item)
        ]

    def id_has_changed(self, content_item: ContentTypes) -> bool:
        """Check if the ID of the content item has changed.

        Args:
            content_item (ContentTypes): The metadata object.

        Returns:
            bool: Wether the ID of the content item has changed or not.
        """
        old_obj = cast(ContentTypes, content_item.old_base_content_object)
        id_has_changed = content_item.object_id != old_obj.object_id
        if id_has_changed:
            self.old_id[content_item.name] = old_obj.object_id
        return id_has_changed

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.object_id = self.old_id[content_item.name]
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.object_id),
            content_object=content_item,
        )
