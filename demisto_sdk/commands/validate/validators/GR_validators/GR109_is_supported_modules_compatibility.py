from __future__ import annotations

from abc import ABC
from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import PlatformSupportedModules
from demisto_sdk.commands.common.logger import logger
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
    # Controls whether to check mandatory (True) or non-mandatory (False) USES relationships.
    # Subclasses can override this to change the dependency type being validated.
    mandatory_dependency: bool = True

    def get_missing_modules_by_dependency(self, content_item) -> dict[str, list[str]]:
        """Get missing modules for each dependency of a content item.

        Args:
            content_item: The content item to check dependencies for

        Returns:
            dict: A dictionary mapping dependency IDs to lists of missing modules
        """
        missing_modules_by_dependency: dict[str, list[str]] = {}

        content_item_name = getattr(content_item, "name", repr(content_item))
        content_item_type = type(content_item).__name__
        content_item_id = getattr(content_item, "object_id", repr(content_item))
        content_item_supported_modules = getattr(content_item, "supportedModules", None)
        uses_list = list(content_item.uses)

        logger.error(
            f"[GR109] get_missing_modules_by_dependency called — "
            f"content_item='{content_item_name}' (type={content_item_type}, id={content_item_id}) "
            f"supportedModules={content_item_supported_modules} "
            f"mandatory_dependency={self.mandatory_dependency} "
            f"total uses={len(uses_list)}"
        )

        for dependency in uses_list:
            dep_target = dependency.content_item_to
            dep_target_type = type(dep_target).__name__
            dep_target_id = getattr(dep_target, "object_id", repr(dep_target))
            dep_target_name = getattr(dep_target, "name", repr(dep_target))
            dep_mandatorily = getattr(dependency, "mandatorily", None)
            dep_node_id = getattr(dep_target, "node_id", "")
            dep_not_in_repo = getattr(dep_target, "not_in_repository", None)
            dep_has_supported_modules = hasattr(dep_target, "supportedModules")
            dep_supported_modules = getattr(
                dep_target, "supportedModules", "<MISSING ATTR>"
            )

            logger.error(
                f"[GR109] Iterating dependency — "
                f"content_item='{content_item_name}' (type={content_item_type}) "
                f"depends on '{dep_target_id}' (name='{dep_target_name}', type={dep_target_type}) "
                f"mandatorily={dep_mandatorily} "
                f"dep.supportedModules={dep_supported_modules} "
                f"dep.has_supportedModules_attr={dep_has_supported_modules} "
                f"dep.node_id='{dep_node_id}' "
                f"dep.not_in_repository={dep_not_in_repo}"
            )

            # Filter by mandatory/non-mandatory based on the class member
            if dep_mandatorily != self.mandatory_dependency:
                logger.error(
                    f"[GR109] Skipping dependency '{dep_target_id}' (type={dep_target_type}) — "
                    f"mandatorily={dep_mandatorily} != expected={self.mandatory_dependency}"
                )
                continue

            # Guard: detect UnknownContent or any object missing supportedModules attribute
            if not dep_has_supported_modules:
                logger.error(
                    f"[GR109] Unexpected dependency target type — "
                    f"content_item='{content_item_name}' (type={content_item_type}) "
                    f"depends on '{dep_target_id}' (type={dep_target_type}) "
                    f"which has no 'supportedModules'. "
                    f"node_id='{dep_node_id}', not_in_repository={dep_not_in_repo}"
                )
                continue

            # Get modules supported by the content item but not by its dependency
            effective_modules = content_item_supported_modules or [
                sm.value for sm in PlatformSupportedModules
            ]
            logger.error(
                f"[GR109] Checking module compatibility — "
                f"content_item='{content_item_name}' effective_modules={effective_modules} "
                f"vs dep='{dep_target_id}' (type={dep_target_type}) supportedModules={dep_supported_modules}"
            )

            missing_modules = [
                module
                for module in effective_modules
                if module not in dep_target.supportedModules
            ]

            logger.error(
                f"[GR109] Module check result — "
                f"content_item='{content_item_name}' depends on '{dep_target_id}' "
                f"missing_modules={missing_modules}"
            )

            if missing_modules:
                missing_modules_by_dependency[dep_target_id] = missing_modules

        logger.error(
            f"[GR109] get_missing_modules_by_dependency result — "
            f"content_item='{content_item_name}' (type={content_item_type}) "
            f"missing_modules_by_dependency={missing_modules_by_dependency}"
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
            # At this point, we assume the mismatch is already established
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

        logger.error(
            f"[GR109] obtain_invalid_content_items_using_graph — "
            f"validate_all_files={validate_all_files} "
            f"mandatory_dependency={self.mandatory_dependency} "
            f"target_content_item_ids={target_content_item_ids}"
        )

        mismatched_dependencies = (
            self.graph.find_content_items_with_module_mismatch_dependencies(
                target_content_item_ids, self.mandatory_dependency
            )
        )

        logger.error(
            f"[GR109] find_content_items_with_module_mismatch_dependencies returned "
            f"{len(mismatched_dependencies)} items: "
            f"{[getattr(item, 'object_id', repr(item)) for item in mismatched_dependencies]}"
        )

        if self.mandatory_dependency:
            mismatched_commands = (
                self.graph.find_content_items_with_module_mismatch_commands(
                    target_content_item_ids
                )
            )
            logger.error(
                f"[GR109] find_content_items_with_module_mismatch_commands returned "
                f"{len(mismatched_commands)} items: "
                f"{[getattr(item, 'object_id', repr(item)) for item in mismatched_commands]}"
            )
        else:
            mismatched_commands = []

        mismatched_content_items = (
            self.graph.find_content_items_with_module_mismatch_content_items(
                target_content_item_ids, self.mandatory_dependency
            )
        )

        logger.error(
            f"[GR109] find_content_items_with_module_mismatch_content_items returned "
            f"{len(mismatched_content_items)} items: "
            f"{[getattr(item, 'object_id', repr(item)) for item in mismatched_content_items]}"
        )

        results: List[ValidationResult] = []

        # Process items with mismatched dependencies
        for invalid_item in mismatched_dependencies:
            item_name = getattr(invalid_item, "name", repr(invalid_item))
            item_type = type(invalid_item).__name__
            item_id = getattr(invalid_item, "object_id", repr(invalid_item))
            item_supported_modules = getattr(invalid_item, "supportedModules", None)
            item_uses_list = list(getattr(invalid_item, "uses", []))

            logger.error(
                f"[GR109] Processing mismatched dependency item — "
                f"content_item='{item_name}' (type={item_type}, id={item_id}) "
                f"supportedModules={item_supported_modules} "
                f"uses_count={len(item_uses_list)}"
            )

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
                dependency_type = (
                    "mandatory" if self.mandatory_dependency else "non-mandatory"
                )
                results.append(
                    ValidationResult(
                        validator=self,
                        message=f"Module compatibility issue detected for {dependency_type} dependency: {formatted_message}. Make sure the commands used are supported by the same modules as the content item.",
                        content_object=invalid_item,
                    )
                )
        return results
