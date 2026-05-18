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

        content_item_id = getattr(content_item, "object_id", repr(content_item))
        content_item_type = type(content_item).__name__
        content_item_modules = getattr(content_item, "supportedModules", None)
        all_uses = list(content_item.uses)

        logger.error(
            f"[GR109][get_missing_modules_by_dependency] "
            f"Checking content_item={content_item_id!r} (type={content_item_type}) | "
            f"supportedModules={content_item_modules!r} | "
            f"mandatory_dependency={self.mandatory_dependency!r} | "
            f"total uses relationships={len(all_uses)}"
        )

        for i, dependency in enumerate(all_uses):
            dep_mandatorily = getattr(dependency, "mandatorily", "<unknown>")
            dep_target = dependency.content_item_to
            dep_target_id: str = (
                getattr(dep_target, "object_id", None)
                or getattr(dep_target, "name", None)
                or repr(dep_target)
            )
            dep_target_type = type(dep_target).__name__
            dep_target_has_supported_modules = hasattr(dep_target, "supportedModules")
            dep_target_supported_modules = getattr(
                dep_target, "supportedModules", "<NO ATTR>"
            )
            dep_target_not_in_repo = getattr(
                dep_target, "not_in_repository", "<unknown>"
            )

            logger.error(
                f"[GR109][get_missing_modules_by_dependency] "
                f"  dep[{i}]: target={dep_target_id!r} (type={dep_target_type}) | "
                f"mandatorily={dep_mandatorily!r} | "
                f"has_supportedModules={dep_target_has_supported_modules} | "
                f"supportedModules={dep_target_supported_modules!r} | "
                f"not_in_repository={dep_target_not_in_repo!r}"
            )

            # Filter by mandatory/non-mandatory based on the class member
            if dep_mandatorily != self.mandatory_dependency:
                logger.error(
                    f"[GR109][get_missing_modules_by_dependency] "
                    f"    SKIP dep[{i}] {dep_target_id!r}: mandatorily={dep_mandatorily!r} "
                    f"!= self.mandatory_dependency={self.mandatory_dependency!r}"
                )
                continue

            if not dep_target_has_supported_modules:
                logger.error(
                    f"[GR109][get_missing_modules_by_dependency] "
                    f"  *** CRASH RISK: dep[{i}] target={dep_target_id!r} (type={dep_target_type}) "
                    f"has NO 'supportedModules' attribute! ***\n"
                    f"      content_item={content_item_id!r} (type={content_item_type})\n"
                    f"      dep_target not_in_repository={dep_target_not_in_repo!r}\n"
                    f"      dep_target dir={[a for a in dir(dep_target) if not a.startswith('_')]!r}\n"
                    f"      This is an UnknownContent node — skipping to avoid AttributeError."
                )
                # SAFE SKIP: do not attempt to access dep_target.supportedModules
                continue

            # Effective modules for content_item: if None/empty → treat as all platform modules
            effective_content_item_modules = content_item_modules or [
                sm.value for sm in PlatformSupportedModules
            ]

            # Get modules supported by the content item but not by its dependency
            missing_modules = [
                module
                for module in effective_content_item_modules
                if module not in (dep_target_supported_modules or [])
            ]

            logger.error(
                f"[GR109][get_missing_modules_by_dependency] "
                f"    dep[{i}] {dep_target_id!r}: "
                f"effective_content_item_modules={effective_content_item_modules!r} | "
                f"dep_target.supportedModules={dep_target_supported_modules!r} | "
                f"missing_modules={missing_modules!r}"
            )

            if missing_modules:
                logger.error(
                    f"[GR109][get_missing_modules_by_dependency] "
                    f"  *** MISMATCH: content_item={content_item_id!r} -> dep={dep_target_id!r} "
                    f"is missing modules: {missing_modules!r} ***\n"
                    f"      content_item.supportedModules={content_item_modules!r} "
                    f"(effective={effective_content_item_modules!r})\n"
                    f"      dep_target.supportedModules={dep_target_supported_modules!r}\n"
                    f"      mandatory_dependency={self.mandatory_dependency!r}"
                )
                missing_modules_by_dependency[dep_target_id] = missing_modules
            else:
                logger.error(
                    f"[GR109][get_missing_modules_by_dependency] "
                    f"    dep[{i}] {dep_target_id!r}: OK — no missing modules."
                )

        logger.error(
            f"[GR109][get_missing_modules_by_dependency] "
            f"  Result for {content_item_id!r}: {len(missing_modules_by_dependency)} mismatch(es) found. "
            f"Keys: {list(missing_modules_by_dependency.keys())!r}"
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
            f"[GR109][obtain_invalid_content_items_using_graph] "
            f"validate_all_files={validate_all_files!r} | "
            f"mandatory_dependency={self.mandatory_dependency!r} | "
            f"validator_class={type(self).__name__!r} | "
            f"target_content_item_ids count={len(target_content_item_ids)} | "
            f"ids={target_content_item_ids!r}"
        )

        logger.error(
            f"[GR109][obtain_invalid_content_items_using_graph] "
            f"Step 1/3: Calling find_content_items_with_module_mismatch_dependencies "
            f"(mandatory={self.mandatory_dependency!r}) ..."
        )
        mismatched_dependencies = (
            self.graph.find_content_items_with_module_mismatch_dependencies(
                target_content_item_ids, self.mandatory_dependency
            )
        )
        logger.error(
            f"[GR109][obtain_invalid_content_items_using_graph] "
            f"Step 1/3 result: {len(mismatched_dependencies)} item(s) with mismatched dependencies. "
            f"Types: {[type(o).__name__ for o in mismatched_dependencies]!r} | "
            f"IDs: {[getattr(o, 'object_id', repr(o)) for o in mismatched_dependencies]!r}"
        )

        if self.mandatory_dependency:
            logger.error(
                "[GR109][obtain_invalid_content_items_using_graph] "
                "Step 2/3: Calling find_content_items_with_module_mismatch_commands ..."
            )
            mismatched_commands = (
                self.graph.find_content_items_with_module_mismatch_commands(
                    target_content_item_ids
                )
            )
            logger.error(
                f"[GR109][obtain_invalid_content_items_using_graph] "
                f"Step 2/3 result: {len(mismatched_commands)} item(s) with mismatched commands. "
                f"IDs: {[getattr(o, 'object_id', repr(o)) for o in mismatched_commands]!r}"
            )
        else:
            logger.error(
                "[GR109][obtain_invalid_content_items_using_graph] "
                "Step 2/3: SKIPPED (mandatory_dependency=False — commands check only runs for mandatory)."
            )
            mismatched_commands = []

        logger.error(
            f"[GR109][obtain_invalid_content_items_using_graph] "
            f"Step 3/3: Calling find_content_items_with_module_mismatch_content_items "
            f"(mandatory={self.mandatory_dependency!r}) ..."
        )
        mismatched_content_items = (
            self.graph.find_content_items_with_module_mismatch_content_items(
                target_content_item_ids, self.mandatory_dependency
            )
        )
        logger.error(
            f"[GR109][obtain_invalid_content_items_using_graph] "
            f"Step 3/3 result: {len(mismatched_content_items)} item(s) with mismatched content_items. "
            f"IDs: {[getattr(o, 'object_id', repr(o)) for o in mismatched_content_items]!r}"
        )

        results: List[ValidationResult] = []

        # Process items with mismatched dependencies
        logger.error(
            f"[GR109][obtain_invalid_content_items_using_graph] "
            f"Processing {len(mismatched_dependencies)} mismatched_dependencies item(s) ..."
        )
        for invalid_item in mismatched_dependencies:
            item_id = getattr(invalid_item, "object_id", repr(invalid_item))
            item_type = type(invalid_item).__name__
            item_modules = getattr(invalid_item, "supportedModules", "<no attr>")
            item_uses_count = len(list(getattr(invalid_item, "uses", [])))
            logger.error(
                f"[GR109][obtain_invalid_content_items_using_graph] "
                f"  Processing mismatched_dep item: {item_id!r} (type={item_type}) | "
                f"supportedModules={item_modules!r} | uses count={item_uses_count}"
            )
            missing_modules_by_dependency = self.get_missing_modules_by_dependency(
                invalid_item
            )
            if missing_modules_by_dependency:
                formatted_messages = self.format_error_messages(
                    missing_modules_by_dependency
                )
                logger.error(
                    f"[GR109][obtain_invalid_content_items_using_graph] "
                    f"  -> VALIDATION ERROR for {item_id!r}: {formatted_messages!r}"
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
            else:
                logger.error(
                    f"[GR109][obtain_invalid_content_items_using_graph] "
                    f"  -> {item_id!r} was in mismatched_dependencies from graph query "
                    f"but get_missing_modules_by_dependency returned empty — no error emitted."
                )

        # Process items with mismatched commands
        logger.error(
            f"[GR109][obtain_invalid_content_items_using_graph] "
            f"Processing {len(mismatched_commands)} mismatched_commands item(s) ..."
        )
        for invalid_item in mismatched_commands:
            item_id = getattr(invalid_item, "object_id", repr(invalid_item))
            missing_modules_by_item = self.get_missing_modules_by_command(invalid_item)
            if missing_modules_by_item:
                formatted_messages = self.format_error_messages(missing_modules_by_item)
                logger.error(
                    f"[GR109][obtain_invalid_content_items_using_graph] "
                    f"  -> COMMAND MISMATCH ERROR for {item_id!r}: {formatted_messages!r}"
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

        # Process items with mismatched content_items
        logger.error(
            f"[GR109][obtain_invalid_content_items_using_graph] "
            f"Processing {len(mismatched_content_items)} mismatched_content_items item(s) ..."
        )
        for invalid_item in mismatched_content_items:
            item_id = getattr(invalid_item, "object_id", repr(invalid_item))
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
                logger.error(
                    f"[GR109][obtain_invalid_content_items_using_graph] "
                    f"  -> CONTENT_ITEM COMMAND MISMATCH for {item_id!r} "
                    f"(dependency_type={dependency_type!r}): {formatted_message!r}"
                )
                results.append(
                    ValidationResult(
                        validator=self,
                        message=f"Module compatibility issue detected for {dependency_type} dependency: {formatted_message}. Make sure the commands used are supported by the same modules as the content item.",
                        content_object=invalid_item,
                    )
                )

        logger.error(
            f"[GR109][obtain_invalid_content_items_using_graph] "
            f"Done. Total ValidationResult(s) to emit: {len(results)}"
        )
        return results
