
from __future__ import annotations

from abc import ABC
from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.content_graph.objects import Job
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
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[
    Integration,
    Script,
    Pack,
    Playbook,
    Dashboard,
    Classifier,
    IncidentType,
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
    CaseLayoutRule
]

class SupportedModulesCompatibility(BaseValidator[ContentTypes], ABC):
    error_code = "GR109"
    description = "If content_item A depends on content_item B - then `supportedModules` of content_item B should include all `supportedModules` of content_item A"
    rationale = "A content item must have all its mandatory dependencies support the modules it operates on, to ensure it functions correctly."
    error_message = "The following mandatory dependencies missing required modules: {0}"
    related_field = "supportedModules"
    is_auto_fixable = False
    # expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED, GitStatuses.RENAMED]
    related_file_type = [RelatedFileType.SCHEMA]


    def obtain_invalid_content_items_using_graph(
            self, content_items: Iterable[ContentTypes], validate_all_files: bool
        ) -> List[ValidationResult]:
        content_item_ids = (
            [] if validate_all_files else [content_item.object_id for content_item in content_items]
        )
        dependencies = self.graph.find_invalid_content_item_dependencies(
            content_item_ids
        )

        results: List[ValidationResult] = []

        for dependency_item in dependencies:

            modules_unsupported = {
                relationship.content_item_to.object_id: [
                    module for module in dependency_item.supportedModules
                    if module not in relationship.content_item_to.supportedModules
                ] for relationship in dependency_item.uses
            }

            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        ', '.join([
                            f"{name} is missing: [{', '.join([module for module in modules])}]"
                            for name, modules in modules_unsupported.items()
                        ])
                    ),
                    content_object=dependency_item,
                )
            )
        return results
