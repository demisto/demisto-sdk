from __future__ import annotations

from abc import ABC
from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import PlatformSupportedModules
from demisto_sdk.commands.content_graph.objects import Job
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
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
    AgentixAction,
    AgentixAgent,
]


class IsSupportedModulesCompatibility(BaseValidator[ContentTypes], ABC):
    error_code = "GR109"
    description = "For a dependency where Content Item A relies on Content Item B, the supportedModules of Content Item A must be a subset of Content Item B's supportedModules."
    rationale = "When Content Item A has a dependency on Content Item B, Content Item A's supportedModules are restricted to only those modules also present in Content Item B's supportedModules."
    error_message = "The following mandatory dependencies missing required modules: {0}"
    related_field = "supportedModules"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.SCHEMA]

    def append_invalid_dependencies(self, invalid_item, results):
        missing_modules_by_dependency = {}
        for dependency in invalid_item.uses:
            missing_modules = [
                module
                for module in invalid_item.supportedModules
                or [sm.value for sm in PlatformSupportedModules]
                if module not in dependency.content_item_to.supportedModules
            ]
            if missing_modules:
                missing_modules_by_dependency[
                    dependency.content_item_to.object_id
                ] = missing_modules

        return missing_modules_by_dependency
    def append_invalid_commands(self, invalid_item, results):
        for command in invalid_item.commands:
            missing_modules_by_item = {}
            missing_modules = [
                module for module in command.supportedModules
                if module not in invalid_item.supportedSupportedModules
            ]
            
            if missing_modules:
                missing_modules_by_item[invalid_item.object_id] = missing_modules
                
            return missing_modules_by_item

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        target_content_item_ids = (
            []
            if validate_all_files
            else [content_item.object_id for content_item in content_items]
        )

        mismatched_dependencies = (
            self.graph.find_content_items_with_module_mismatch_dependencies(
                target_content_item_ids
            )
        )

        mismatched_commands = (
            self.graph.find_content_items_with_module_mismatch_commands(
                target_content_item_ids
            )
        )

        results: List[ValidationResult] = []

        for invalid_item in mismatched_dependencies:
            missing_modules_by_dependency = self.append_invalid_dependencies(invalid_item, results)
            if missing_modules_by_dependency:
                formatted_messages = []
                for name, modules in missing_modules_by_dependency.items():
                    formatted_messages.append(
                        f"{name} is missing: [{', '.join(modules)}]"
                    )

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            ", ".join(formatted_messages)
                        ),
                        content_object=invalid_item,
                    )
                )

        for invalid_item in mismatched_commands:
            missing_modules_by_item = self.append_invalid_commands(invalid_item, results)
            if missing_modules_by_item:
                formatted_messages = []
                for name, modules in missing_modules_by_item.items():
                    formatted_messages.append(
                        f"{name} is missing: [{', '.join(modules)}]"
                    )

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            ", ".join(formatted_messages)
                        ),
                        content_object=invalid_item,
                    )
                )


        return results
