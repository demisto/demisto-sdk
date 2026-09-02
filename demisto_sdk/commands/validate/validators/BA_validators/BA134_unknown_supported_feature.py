from __future__ import annotations

from typing import Iterable, List, Optional, Set, Union

from demisto_sdk.commands.common.regional_rules import RegionalRules
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
    Dashboard,
    Classifier,
    IncidentType,
    Job,
    Layout,
    Mapper,
    Wizard,
    CorrelationRule,
    IncidentField,
    IndicatorField,
    IndicatorType,
    LayoutRule,
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


class UnknownSupportedFeatureValidator(BaseValidator[ContentTypes]):
    error_code = "BA134"
    description = (
        "Validates that every value in a content item's 'supportedFeatures' is "
        "declared under 'supported_features' in Config/regional_rules.json."
    )
    rationale = (
        "A feature that appears in no region block and not in global does not "
        "exist as far as the platform is concerned, so an item declaring it "
        "would never be enabled anywhere."
    )
    error_message = (
        "The content item declares the following unknown supported features: {0}. "
        "These values do not appear under 'supported_features' in "
        "Config/regional_rules.json, neither in 'global' nor in any region block. "
        "The known features are: {1}."
    )
    related_field = "supportedFeatures"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        rules = RegionalRules.from_path()
        if rules is None:
            # No rules file (e.g. running outside the content repo) means there
            # is nothing to validate against.
            return []

        known_features = rules.all_supported_features()

        results = []
        for content_item in content_items:
            unknown = self._unknown_features(content_item, known_features)
            if unknown:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            ", ".join(sorted(unknown)),
                            ", ".join(sorted(known_features)) or "none",
                        ),
                        content_object=content_item,
                    )
                )
        return results

    def _unknown_features(
        self, item: ContentTypes, known_features: Set[str]
    ) -> Set[str]:
        """Returns the item's declared features that no region or global enables.

        Only the item's own value is checked - an inherited one is validated on
        the pack itself, to avoid reporting it on every item in the pack.
        """
        item_features: Optional[List[str]] = getattr(item, "supportedFeatures", None)
        if not item_features:
            return set()
        return set(item_features).difference(known_features)
