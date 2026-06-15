from __future__ import annotations

from typing import ClassVar, Iterable, List, Union

from demisto_sdk.commands.common.constants import (
    GitStatuses,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import get_declared_supported_modules
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


class SupportedModulesWithoutPlatformValidator(BaseValidator[ContentTypes]):
    error_code = "BA132"
    description = (
        "Validates that a content item does not declare 'supportedModules' unless "
        "'platform' is present in its marketplaces."
    )
    rationale = (
        "The 'supportedModules' field is only meaningful for platform content "
        "items (those that include 'platform' in their marketplaces). Declaring "
        "supported modules without 'platform' in the marketplaces has no effect "
        "and indicates a misconfigured content item."
    )
    error_message = (
        "The content item declares 'supportedModules' but does not include "
        "'platform' in its marketplaces. Either add 'platform' to the marketplaces "
        "or remove the 'supportedModules' field."
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
        """Identify content items that declare supportedModules without platform.

        The 'supportedModules' are resolved through the inheritance chain
        (item -> pack), so an item that inherits its modules from its pack is
        treated the same as one that declares them directly. The platform
        default ('all modules') is intentionally NOT applied here - only
        explicitly declared modules count.

        Args:
            content_items (Iterable[ContentTypes]): The content items to validate.

        Returns:
            List[ValidationResult]: A validation result per content item that
            declares 'supportedModules' while 'platform' is absent from its
            marketplaces.
        """
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if MarketplaceVersions.PLATFORM not in content_item.marketplaces
            and get_declared_supported_modules(content_item)
        ]
