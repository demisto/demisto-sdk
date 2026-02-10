from __future__ import annotations

from typing import Iterable, List, cast

from git import Union

from demisto_sdk.commands.common.constants import GitStatuses, PlatformSupportedModules
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
    CaseLayoutRule,
]


class IsSupportedModulesRemoved(BaseValidator[ContentTypes]):
    error_code = "BC115"
    description = (
        "Ensure that no support module are removed from an existing content item."
    )
    rationale = "Removing a support module for content item can break functionality for customers."
    error_message = "The following support modules have been removed from the integration {}. Removing supported modules is not allowed, Please undo."
    related_field = "supportedModules"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]
    related_file_type = [RelatedFileType.SCHEMA]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    ", ".join(map(repr, sorted(difference)))
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.old_base_content_object is not None
            and (
                difference := self.removed_parameters(
                    cast(ContentTypes, content_item.old_base_content_object),
                    content_item,
                )
            )
        ]

    def removed_parameters(
        self, old_item: ContentTypes, new_item: ContentTypes
    ) -> set[str]:
        """
        Calculates the set of supported modules that were removed from the old item
        compared to the new item.
        """
        default_modules = [sm.value for sm in PlatformSupportedModules]

        def get_modules(item: ContentTypes) -> set:
            """
            Resolves the definitive list of supported modules for an item,
            falling back to its pack's modules or the platform defaults.
            """
            modules = item.supportedModules
            if not modules and not isinstance(item, Pack):
                modules = item.pack.supportedModules

            return set(modules or default_modules)

        old_params = get_modules(old_item)
        new_params = get_modules(new_item)

        return old_params.difference(new_params)
