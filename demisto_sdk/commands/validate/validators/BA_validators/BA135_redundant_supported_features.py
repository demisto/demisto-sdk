from __future__ import annotations

from typing import Iterable, List, Optional, Union

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


class RedundantSupportedFeaturesValidator(BaseValidator[ContentTypes]):
    error_code = "BA135"
    description = (
        "Validates that a content item does not redeclare the exact "
        "'supportedFeatures' list already defined by its pack."
    )
    rationale = (
        "An item that omits the field inherits the pack's value, so repeating "
        "that value verbatim has no effect and only creates a second place to "
        "update when the pack's features change."
    )
    error_message = (
        "The content item's 'supportedFeatures' ({0}) is identical to its pack's. "
        "Remove the field from the item - it inherits the pack's value when the "
        "key is omitted."
    )
    related_field = "supportedFeatures"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(sorted(features))),
                content_object=content_item,
            )
            for content_item in content_items
            # `_is_redundant` already guarantees a non-empty value, but binding
            # it here keeps the type narrowed for the message above.
            if self._is_redundant(content_item)
            and (features := getattr(content_item, "supportedFeatures", None) or [])
        ]

    def _is_redundant(self, item: ContentTypes) -> bool:
        """Whether the item's declared features match its pack's exactly.

        Order and repetition are irrelevant to the comparison, so the values
        are compared as sets.
        """
        item_features: Optional[List[str]] = getattr(item, "supportedFeatures", None)
        if not item_features:
            return False

        pack = getattr(item, "pack", None)
        pack_features: Optional[List[str]] = (
            getattr(pack, "supportedFeatures", None) if pack else None
        )
        if not pack_features:
            return False

        return set(item_features) == set(pack_features)
