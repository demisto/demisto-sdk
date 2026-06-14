from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
    PlatformSupportedModules,
)
from demisto_sdk.commands.common.tools import get_content_item_supported_modules
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_action_test import (
    AgentixActionTest,
)
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
from demisto_sdk.commands.content_graph.objects.list import List as ListObject
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.pre_process_rule import PreProcessRule
from demisto_sdk.commands.content_graph.objects.report import Report
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.objects.test_script import TestScript
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.content_graph.objects.xdrc_template import XDRCTemplate
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[
    AgentixAction,
    AgentixActionTest,
    AgentixAgent,
    AssetsModelingRule,
    CaseField,
    CaseLayout,
    CaseLayoutRule,
    Classifier,
    CorrelationRule,
    Dashboard,
    GenericDefinition,
    GenericField,
    GenericModule,
    GenericType,
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
    Pack,
    ParsingRule,
    Playbook,
    PreProcessRule,
    Report,
    Script,
    TestPlaybook,
    TestScript,
    Trigger,
    Widget,
    Wizard,
    XDRCTemplate,
    XSIAMDashboard,
    XSIAMReport,
]


class MarketplaceV2WithoutPlatformValidator(BaseValidator[ContentTypes]):
    error_code = "BA130"
    description = (
        "Validates that content items with 'marketplacev2' also have 'platform' "
        "in their marketplaces and 'xsiam' in their supported modules — set "
        "directly, inherited from the pack, or via defaults."
    )
    rationale = (
        "Content items with 'marketplacev2' must also have 'platform' and 'xsiam' "
        "in their supported modules. These values don't have to be set directly on "
        "the item — they can be inherited from the pack or resolved from defaults."
    )
    error_message = (
        "The content item has 'marketplacev2' but is missing 'platform' in its "
        "marketplaces and/or 'xsiam' in its supported modules (these can be set "
        "directly, inherited from the pack, or resolved from defaults)."
    )
    fix_message = (
        "Added 'platform' to marketplaces and/or 'xsiam' to supported modules."
    )
    related_field = "marketplaces"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if MarketplaceVersions.MarketplaceV2 in content_item.marketplaces
            and PlatformSupportedModules.XSIAM
            not in get_content_item_supported_modules(content_item)
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        supported_modules = get_content_item_supported_modules(content_item)
        if not supported_modules:
            # No platform in marketplaces - add platform and set xsiam
            content_item.marketplaces.append(MarketplaceVersions.PLATFORM)
            content_item.supportedModules = [PlatformSupportedModules.XSIAM.value]
        else:
            # Platform exists but xsiam is missing - add xsiam to the resolved modules
            content_item.supportedModules = list(
                supported_modules | {PlatformSupportedModules.XSIAM.value}
            )

        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
