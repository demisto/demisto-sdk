
from __future__ import annotations

from abc import ABC

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.job import Job
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.content_graph.objects.layout_rule import LayoutRule
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.report import Report
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.content_graph.objects.generic_definition import GenericDefinition
from demisto_sdk.commands.content_graph.objects.generic_field import GenericField
from demisto_sdk.commands.content_graph.objects.generic_module import GenericModule
from demisto_sdk.commands.content_graph.objects.generic_type import GenericType
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport
from demisto_sdk.commands.content_graph.objects.case_field
from demisto_sdk.commands.content_graph.objects.case_layout
from demisto_sdk.commands.content_graph.objects.case_layout_rule
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook, Pack, Dashboard, Classifier, Job, Layout, Mapper, Wizard, CorrelationRule, IncidentField, IncidentType, IndicatorField, IndicatorType, LayoutRule, Layout, ModelingRule, ParsingRule, Report, TestPlaybook, Trigger, Widget, GenericDefinition, GenericField, GenericModule, GenericType, XSIAMDashboard, XSIAMReport, CaseField, CaseLayout, CaseLayoutRule]


class IsUsingUnknownContentValidator(BaseValidator[ContentTypes]):
    error_code = "GR103"
    description = "Validates that there is no usage of unknown content items"
    rationale = "Content items should only use other content items that exist in the repository."
    error_message = "Content item '{0}' using content items: '{1}' which cannot be found in the repository."
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]


    def obtain_invalid_content_items_using_graph(self, content_items: Iterable[ContentTypes], validate_all_files: bool) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            file_path_to_validate =[content_item.path] if not validate_all_files else []
            uses_unknown_content = self.graph.get_unknown_content_uses(file_path = file_path_to_validate,raises_error=True, include_optional=True)
        if uses_unknown_content:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(content_item.name, ", ".join(uses_unknown_content)),
                        content_object=content_item,
                    )
                )

        return results

