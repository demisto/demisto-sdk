from __future__ import annotations

from abc import ABC
from collections import defaultdict
from typing import Dict, Iterable, List, Union

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
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


class IsDeprecatedContentItemInUsageValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR107"
    description = (
        "Validates that deprecated content items are not used in other content items."
    )
    rationale = "Using deprecated content items can lead to unexpected behavior and should be avoided."
    error_message = "The item '{item_id}' is using the following deprecated items: {deprecated_items}"
    related_field = "deprecated"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        content_item_paths: List = (
            []
            if validate_all_files
            else [
                str(content_item.path.relative_to(CONTENT_PATH))
                for content_item in content_items
            ]
        )
        # Group results by content item
        grouped_results: Dict[BaseContent, Dict[str, set]] = defaultdict(
            lambda: {"deprecated_items": set()}
        )
        for item in self.graph.find_items_using_deprecated_items(content_item_paths):
            for item_using_deprecated in item.content_items_using_deprecated:
                grouped_results[item_using_deprecated]["deprecated_items"].add(  # type: ignore[index]
                    item.deprecated_item_id
                )
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    item_id=item_using_deprecated.object_id,
                    deprecated_items=", ".join(data["deprecated_items"]),
                ),
                content_object=item_using_deprecated,
            )
            for item_using_deprecated, data in grouped_results.items()
        ]
