from __future__ import annotations

from typing import Iterable, List, Optional, Set, Union

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
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
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


class IsSupportedFeaturesSubsetOfPack(BaseValidator[ContentTypes]):
    error_code = "ST115"
    description = (
        "Ensure that all supported features of a content item are a subset of "
        "its Content Pack's supported features."
    )
    rationale = (
        "A pack that declares supportedFeatures restricts where the whole pack "
        "is available. An item cannot be available somewhere its pack is not, "
        "so declaring a feature outside the pack's list is unachievable."
    )
    error_message = (
        "The following supported features are defined for the item but not allowed "
        "by its pack: {}. Please ensure the item's supportedFeatures are a subset "
        "of the pack's supportedFeatures."
    )
    related_field = "supportedFeatures"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.SCHEMA]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(sorted(diff))),
                content_object=content_item,
            )
            for content_item in content_items
            if (diff := self._features_not_allowed_by_pack(content_item))
        ]

    def _features_not_allowed_by_pack(self, item: ContentTypes) -> Set[str]:
        """Returns the item's features that its pack does not allow.

        Valid (empty set) when the item declares nothing and so inherits the
        pack's value, or when the pack declares nothing and so restricts nothing.
        """
        item_features: Optional[List[str]] = getattr(item, "supportedFeatures", None)
        if not item_features:
            return set()

        pack = getattr(item, "pack", None)
        pack_features: Optional[List[str]] = (
            getattr(pack, "supportedFeatures", None) if pack else None
        )
        if not pack_features:
            # Pack is supported everywhere - the item may declare any feature.
            return set()

        return set(item_features).difference(pack_features)
