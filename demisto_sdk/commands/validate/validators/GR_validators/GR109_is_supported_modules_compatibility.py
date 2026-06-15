from __future__ import annotations

from abc import ABC
from typing import Iterable, List, Union
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects import Job
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.case_field import CaseField
from demisto_sdk.commands.content_graph.objects.case_layout import CaseLayout
from demisto_sdk.commands.content_graph.objects.case_layout_rule import CaseLayoutRule
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.collection import Collection
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
    Collection,
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

    def get_missing_modules_by_command(self, content_item) -> dict[str, list[str]]:
        """Get missing modules for each command of a content item.

        Args:
            content_item: The content item to check commands for

        Returns:
            dict: A dictionary mapping the content item ID to lists of missing modules per command
        """
        logger.info(f"[GR109] Checking command module compatibility for content item: {content_item.object_id}")
        missing_modules_by_item: dict[str, list[str]] = {}

        for command in content_item.commands:
            logger.info(f"[GR109] Checking command: {command.object_id} for content item: {content_item.object_id}")
            # Get modules supported by the command but not by the content item
            missing_modules = [
                module
                for module in command.supportedModules
                if module not in content_item.supportedModules
            ]

            if missing_modules:
                logger.info(f"[GR109] Found missing modules for command {command.object_id}: {missing_modules}")
                if content_item.object_id not in missing_modules_by_item:
                    missing_modules_by_item[content_item.object_id] = []
                missing_modules_by_item[content_item.object_id].extend(missing_modules)

        logger.info(f"[GR109] Completed command check for {content_item.object_id}. Missing modules by item: {missing_modules_by_item}")
        return missing_modules_by_item

    def get_commands_with_missing_modules_by_content_item(
        self,
        item,
        commands_with_missing_modules_by_content_item: dict,
        incompatible_commands: list[str],
    ):
        """Populate the incompatible commands for a content item.

        The set of genuinely module-incompatible commands is computed by the graph
        query (``get_supported_modules_mismatch_content_items``) using the command's
        HAS_COMMAND ``supportedModules`` - data that is not available on the loaded
        content-item object. Therefore this method consumes the precomputed list of
        incompatible command names rather than re-deriving it from ``item.uses``
        (which would incorrectly flag every command the item uses, including
        compatible, module-agnostic ones).

        Args:
            item: The content item the incompatible commands belong to.
            commands_with_missing_modules_by_content_item: Dictionary to populate with
                commands that have missing modules, keyed by content item object_id.
            incompatible_commands: The precomputed list of incompatible command names
                for this content item, as returned by the graph query.
        """
        logger.info(f"[GR109] Getting commands with missing modules for content item: {item.object_id}")
        if not incompatible_commands:
            logger.info(f"[GR109] No incompatible commands for {item.object_id}.")
            return
        commands_with_missing_modules_by_content_item[item.object_id] = list(
            incompatible_commands
        )
        logger.info(f"[GR109] Completed commands check for {item.object_id}. Commands with missing modules: {commands_with_missing_modules_by_content_item}")

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
        logger.info(f"[GR109] Starting graph-based validation. validate_all_files={validate_all_files}")
        target_content_item_ids = (
            []
            if validate_all_files
            else [content_item.object_id for content_item in content_items]
        )
        logger.info(f"[GR109] Target content item IDs: {target_content_item_ids}")

        logger.info("[GR109] Querying graph for content items with module mismatch dependencies")
        (
            mismatched_dependencies,
            missing_modules_by_dependency_by_item,
        ) = self.graph.find_content_items_with_module_mismatch_dependencies(
            target_content_item_ids, self.mandatory_dependency
        )
        logger.info(f"[GR109] Found {len(mismatched_dependencies)} items with mismatched dependencies")

        logger.info("[GR109] Querying graph for content items with module mismatch commands")
        if self.mandatory_dependency:
            mismatched_commands = (
                self.graph.find_content_items_with_module_mismatch_commands(
                    target_content_item_ids
                )
            )
            logger.info(f"[GR109] Found {len(mismatched_commands)} items with mismatched commands")
        else:
            mismatched_commands = []

        logger.info("[GR109] Querying graph for content items with module mismatch content items")
        (
            mismatched_content_items,
            incompatible_commands_by_item,
        ) = self.graph.find_content_items_with_module_mismatch_content_items(
            target_content_item_ids, self.mandatory_dependency
        )
        logger.info(f"[GR109] Found {len(mismatched_content_items)} items with mismatched content items")

        results: List[ValidationResult] = []

        # Process items with mismatched dependencies
        logger.info("[GR109] Processing items with mismatched dependencies")
        for invalid_item in mismatched_dependencies:
            logger.info(f"[GR109] Processing invalid item with mismatched dependency: {invalid_item.object_id}")
            # The missing modules per dependency are computed by the graph query
            # against each dependency's own supportedModules, because that data is
            # not reliably available on the dependency object once loaded into
            # memory (e.g. command nodes reached via USES do not carry their
            # HAS_COMMAND supportedModules). This ensures the message lists only the
            # modules genuinely unsupported by each dependency.
            missing_modules_by_dependency = {
                dependency_id: modules
                for dependency_id, modules in missing_modules_by_dependency_by_item.get(
                    invalid_item.object_id, {}
                ).items()
                if modules
            }
            if missing_modules_by_dependency:
                formatted_messages = self.format_error_messages(
                    missing_modules_by_dependency
                )
                logger.info(f"[GR109] Adding validation result for {invalid_item.object_id}: {formatted_messages}")
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
        logger.info("[GR109] Processing items with mismatched commands")
        for invalid_item in mismatched_commands:
            logger.info(f"[GR109] Processing invalid item with mismatched command: {invalid_item.object_id}")
            missing_modules_by_item = self.get_missing_modules_by_command(invalid_item)
            if missing_modules_by_item:
                formatted_messages = self.format_error_messages(missing_modules_by_item)
                logger.info(f"[GR109] Adding validation result for {invalid_item.object_id}: {formatted_messages}")
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
        logger.info("[GR109] Processing items with mismatched content items")
        for invalid_item in mismatched_content_items:
            logger.info(f"[GR109] Processing invalid item with mismatched content item: {invalid_item.object_id}")
            commands_with_missing_modules: dict[str, list[str]] = {}
            self.get_commands_with_missing_modules_by_content_item(
                invalid_item,
                commands_with_missing_modules,
                incompatible_commands_by_item.get(invalid_item.object_id, []),
            )
            if commands_with_missing_modules:
                formatted_message = self.format_commands_error_message(
                    commands_with_missing_modules
                )
                logger.info(f"[GR109] Adding validation result for {invalid_item.object_id}: {formatted_message}")
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
        logger.info(f"[GR109] Validation complete. Total validation results: {len(results)}")
        return results
