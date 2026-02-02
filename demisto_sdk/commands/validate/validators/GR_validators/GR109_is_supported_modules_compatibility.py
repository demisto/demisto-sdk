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

    def get_missing_modules_by_dependency(self, content_item) -> dict[str, list[str]]:
        """Get missing modules for each dependency of a content item.

        Args:
            content_item: The content item to check dependencies for

        Returns:
            dict: A dictionary mapping dependency IDs to lists of missing modules
        """
        missing_modules_by_dependency: dict[str, list[str]] = {}
        for dependency in content_item.uses:
            # Get modules supported by the content item but not by its dependency
            missing_modules = [
                module
                for module in content_item.supportedModules
                or [sm.value for sm in PlatformSupportedModules]
                if module not in dependency.content_item_to.supportedModules
            ]
            if missing_modules:
                missing_modules_by_dependency[dependency.content_item_to.object_id] = (
                    missing_modules
                )

        return missing_modules_by_dependency

    def get_missing_modules_by_command(self, content_item) -> dict[str, list[str]]:
        """Get missing modules for each command of a content item.

        Args:
            content_item: The content item to check commands for

        Returns:
            dict: A dictionary mapping the content item ID to lists of missing modules per command
        """
        missing_modules_by_item: dict[str, list[str]] = {}

        for command in content_item.commands:
            # Get modules supported by the command but not by the content item
            missing_modules = [
                module
                for module in command.supportedModules
                if module not in content_item.supportedModules
            ]

            if missing_modules:
                if content_item.object_id not in missing_modules_by_item:
                    missing_modules_by_item[content_item.object_id] = []
                missing_modules_by_item[content_item.object_id].extend(missing_modules)

        return missing_modules_by_item

    def get_commands_with_missing_modules_by_content_item(
        self, item, commands_with_missing_modules_by_content_item: dict
    ):
        """Get commands with missing modules for a content item.

        Args:
            item: The content item to check commands for
            commands_with_missing_modules_by_content_item: Dictionary to populate with commands that have missing modules

        Returns:
            dict: A dictionary mapping content item IDs to lists of command IDs
        """
        for rel in item.uses:
            command = rel.content_item_to
            # Get the command's supported modules from the relationship
            command_supported_modules = rel.supportedModules or []
            
            # Only add if there's an actual mismatch:
            # - Command has specific modules AND
            # - Content item supports a module that the command doesn't support
            if command_supported_modules and any(
                module not in command_supported_modules
                for module in (item.supportedModules or [])
            ):
                if item.object_id not in commands_with_missing_modules_by_content_item:
                    commands_with_missing_modules_by_content_item[item.object_id] = []
                # Add the command ID to the list
                commands_with_missing_modules_by_content_item[item.object_id].append(
                    command.object_id
                )

    def format_error_messages(self, missing_modules_dict):
        """Format error messages for missing modules.

        Args:
            missing_modules_dict: Dictionary mapping object IDs to lists of missing modules

        Returns:
            list: Formatted error messages
        """
        formatted_messages = []
        for object_id, modules in missing_modules_dict.items():
            formatted_messages.append(f"{object_id} is missing: [{', '.join(modules)}]")
        return formatted_messages

    def format_commands_error_message(self, commands_with_missing_modules: dict) -> str:
        """Format error message for commands with missing modules.

        Args:
            commands_with_missing_modules: Dictionary mapping content item IDs to lists of command IDs

        Returns:
            str: Formatted error message
        """
        formatted_messages = []
        for content_item_id, commands in commands_with_missing_modules.items():
            formatted_messages.append(
                f"Content item '{content_item_id}' has incompatible commands: [{', '.join(commands)}]"
            )
        return ", ".join(formatted_messages)

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

        mismatched_content_items = (
            self.graph.find_content_items_with_module_mismatch_content_items(
                target_content_item_ids
            )
        )

        results: List[ValidationResult] = []

        # Process items with mismatched dependencies
        for invalid_item in mismatched_dependencies:
            missing_modules_by_dependency = self.get_missing_modules_by_dependency(
                invalid_item
            )
            if missing_modules_by_dependency:
                formatted_messages = self.format_error_messages(
                    missing_modules_by_dependency
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

        # Process items with mismatched commands
        for invalid_item in mismatched_commands:
            missing_modules_by_item = self.get_missing_modules_by_command(invalid_item)
            if missing_modules_by_item:
                formatted_messages = self.format_error_messages(missing_modules_by_item)
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            ", ".join(formatted_messages)
                        ),
                        content_object=invalid_item,
                    )
                )

        # Process items with mismatched content_items
        for invalid_item in mismatched_content_items:
            commands_with_missing_modules: dict[str, list[str]] = {}
            self.get_commands_with_missing_modules_by_content_item(
                invalid_item, commands_with_missing_modules
            )
            if commands_with_missing_modules:
                formatted_message = self.format_commands_error_message(
                    commands_with_missing_modules
                )
                results.append(
                    ValidationResult(
                        validator=self,
                        message=f"Module compatibility issue detected: {formatted_message}. Make sure the commands used are supported by the same modules as the content item.",
                        content_object=invalid_item,
                    )
                )
        return results
