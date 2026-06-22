from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List, Set, Union

from demisto_sdk.commands.common.constants import (
    GitStatuses,
    PlatformSupportedModules,
)
from demisto_sdk.commands.common.tools import get_content_item_supported_modules
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.assets_modeling_rule import (
    AssetsModelingRule,
)
from demisto_sdk.commands.content_graph.objects.case_field import CaseField
from demisto_sdk.commands.content_graph.objects.case_layout import CaseLayout
from demisto_sdk.commands.content_graph.objects.case_layout_rule import CaseLayoutRule
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.job import Job
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.layout_rule import LayoutRule
from demisto_sdk.commands.content_graph.objects.list import List as ListObject
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.report import Report
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.content_graph.objects.xdrc_template import XDRCTemplate
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[
    AgentixAction,
    AgentixAgent,
    AssetsModelingRule,
    CaseField,
    CaseLayout,
    CaseLayoutRule,
    Classifier,
    CorrelationRule,
    Dashboard,
    IncidentField,
    IncidentType,
    IndicatorField,
    IndicatorType,
    Integration,
    Job,
    Layout,
    LayoutRule,
    ListObject,
    Mapper,
    ModelingRule,
    ParsingRule,
    Playbook,
    Report,
    Script,
    Trigger,
    Widget,
    Wizard,
    XDRCTemplate,
    XSIAMDashboard,
    XSIAMReport,
]

# The complete set of platform supported modules.
ALL_MODULES: Set[str] = {module.value for module in PlatformSupportedModules}

# Content item types that allow every platform supported module.
XSIAM_AND_AGENTIX: Set[str] = {
    PlatformSupportedModules.XSIAM.value,
    PlatformSupportedModules.AGENTIX.value,
}

# Content item types that allow only the 'xsiam' module.
XSIAM_ONLY: Set[str] = {PlatformSupportedModules.XSIAM.value}

# Mapping of content item type to the set of modules it is allowed to declare in
# its 'supportedModules' field, based on the finalized per-content-type table.
ALLOWED_MODULES_BY_TYPE: Dict[type, Set[str]] = {
    # Full set of modules.
    Integration: ALL_MODULES,
    Script: ALL_MODULES,
    Playbook: ALL_MODULES,
    Layout: ALL_MODULES,
    LayoutRule: ALL_MODULES,
    CaseLayout: ALL_MODULES,
    Trigger: ALL_MODULES,
    AgentixAgent: ALL_MODULES,
    AgentixAction: ALL_MODULES,
    # xsiam + agentix.
    Classifier: XSIAM_AND_AGENTIX,
    CorrelationRule: XSIAM_AND_AGENTIX,
    Dashboard: XSIAM_AND_AGENTIX,
    IncidentField: XSIAM_AND_AGENTIX,
    IncidentType: XSIAM_AND_AGENTIX,
    IndicatorField: XSIAM_AND_AGENTIX,
    IndicatorType: XSIAM_AND_AGENTIX,
    Job: XSIAM_AND_AGENTIX,
    ListObject: XSIAM_AND_AGENTIX,
    Mapper: XSIAM_AND_AGENTIX,
    Report: XSIAM_AND_AGENTIX,
    Widget: XSIAM_AND_AGENTIX,
    CaseField: XSIAM_AND_AGENTIX,
    CaseLayoutRule: XSIAM_AND_AGENTIX,
    # xsiam only.
    ModelingRule: XSIAM_ONLY,
    ParsingRule: XSIAM_ONLY,
    XSIAMDashboard: XSIAM_ONLY,
    XSIAMReport: XSIAM_ONLY,
    Wizard: XSIAM_ONLY,
    XDRCTemplate: XSIAM_ONLY,
    AssetsModelingRule: XSIAM_ONLY,
}


class InvalidSupportedModulesValidator(BaseValidator[ContentTypes]):
    error_code = "BA131"
    description = (
        "Validates that a content item's 'supportedModules' field only contains "
        "module values that are permitted for that content item type."
    )
    rationale = (
        "Each content item type can only run under a specific set of modules. "
        "Declaring a module that is not supported for the item's type results in "
        "content that cannot be loaded correctly by the platform."
    )
    error_message = (
        "The content item '{0}' declares the following unsupported modules: {1}. "
        "The allowed modules for this content item type are: {2}."
    )
    related_field = "supportedModules"
    is_auto_fixable = False
    expected_git_statuses: ClassVar[List[GitStatuses]] = [
        GitStatuses.ADDED,
        GitStatuses.RENAMED,
        GitStatuses.MODIFIED,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        """Identify content items declaring modules not allowed for their type.

        Args:
            content_items (Iterable[ContentTypes]): The content items to validate.

        Returns:
            List[ValidationResult]: A validation result per content item that
            declares one or more unsupported modules.
        """
        results: List[ValidationResult] = []

        for content_item in content_items:
            allowed_modules = self._get_allowed_modules(content_item)
            if allowed_modules is None:
                # Content item type is not covered by the table - skip.
                continue

            # Resolve the modules the platform will actually apply for this item:
            # taken directly from the item, inherited from its pack, or resolved
            # from the platform defaults.
            declared_modules = get_content_item_supported_modules(content_item)
            if not declared_modules:
                # Empty only for non-platform items (no 'platform' marketplace).
                # Platform items always resolve to their own/pack/default modules,
                # so there is nothing to validate for non-platform items.
                continue

            invalid_modules = declared_modules - allowed_modules
            if invalid_modules:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.name,
                            ", ".join(sorted(invalid_modules)),
                            ", ".join(sorted(allowed_modules)) or "none",
                        ),
                        content_object=content_item,
                    )
                )

        return results

    @staticmethod
    def _get_allowed_modules(content_item: ContentTypes) -> Set[str] | None:
        """Resolve the set of allowed modules for the given content item's type.

        Args:
            content_item (ContentTypes): The content item to look up.

        Returns:
            Set[str] | None: The allowed module set for the item's type, or None
            if the type is not covered by the table.
        """
        return ALLOWED_MODULES_BY_TYPE.get(type(content_item))
