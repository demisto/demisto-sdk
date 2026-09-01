from __future__ import annotations

from abc import ABC
from typing import FrozenSet, Iterable, List, Optional, Set, Union

from demisto_sdk.commands.common.regional_rules import RegionalRules
from demisto_sdk.commands.common.tools import (
    get_content_item_supported_features,
    get_relative_path_from_packs_dir,
)
from demisto_sdk.commands.content_graph.objects import (
    AgentixAction,
    AgentixAgent,
    AgentixSkill,
)
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
from demisto_sdk.commands.content_graph.objects.job import Job
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
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[
    Integration,
    Script,
    Playbook,
    Pack,
    Dashboard,
    Classifier,
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
    AgentixSkill,
    Collection,
]


class DuplicateContentIdValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR105"
    description = (
        "Ensures that content items sharing an ID are never active in the same "
        "region, so the platform can always resolve an ID unambiguously."
    )
    rationale = (
        "The same ID may legitimately be reused for variants of a content item, "
        "provided no region receives more than one of them. Two variants active "
        "in the same region cannot be told apart."
    )
    error_message = (
        "Duplicate ID '{0}' also found in {1}. Both items are active in the "
        "following region(s): {2}. {3}"
    )
    related_field = "id"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        paths_of_content_items_to_validate = (
            []
            if validate_all_files
            else [
                get_relative_path_from_packs_dir(str(content_item.path))
                for content_item in content_items
            ]
        )

        # The graph returns every pair sharing a content type and an ID. That
        # is no longer sufficient grounds to fail: a repeated ID is legal as
        # long as the variants are never active in the same region.
        rules = RegionalRules.from_path()

        results = []
        for content_item, duplicates in self.graph.validate_duplicate_ids(
            paths_of_content_items_to_validate
        ):
            for duplicate in duplicates:
                colliding_regions = self._colliding_regions(
                    content_item, duplicate, rules
                )
                if colliding_regions is None:
                    continue
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.object_id,
                            get_relative_path_from_packs_dir(str(duplicate.path)),
                            ", ".join(sorted(colliding_regions)) or "all regions",
                            self._explain(content_item, duplicate),
                        ),
                        content_object=content_item,  # type: ignore[arg-type]
                    )
                )
        return results

    def _colliding_regions(
        self,
        content_item: ContentTypes,
        duplicate: ContentTypes,
        rules: Optional[RegionalRules],
    ) -> Optional[Set[str]]:
        """The regions in which both items are active, or None when they never are.

        Returning ``None`` means the pair is legal and must not be reported;
        an empty set means they collide but the specific regions could not be
        named (see the no-rules fallback below).
        """
        features_a = get_content_item_supported_features(content_item)
        features_b = get_content_item_supported_features(duplicate)

        if rules is None:
            # Without the regional rules we cannot map features to regions, so
            # we fall back to the weaker feature-name test. This is safe in the
            # sense that it never permits an overlap, but it does permit two
            # items whose distinct features happen to share a region - that can
            # only be caught where the config file is available (CI).
            if features_a is None or features_b is None:
                return set()
            return set(features_a & features_b) or None

        regions_a = rules.regions_for_features(features_a)
        regions_b = rules.regions_for_features(features_b)
        return (regions_a & regions_b) or None

    def _explain(self, content_item: ContentTypes, duplicate: ContentTypes) -> str:
        """Explains why the pair collides, in the author's terms."""
        features_a = get_content_item_supported_features(content_item)
        features_b = get_content_item_supported_features(duplicate)

        unrestricted = [
            path
            for path, features in (
                (get_relative_path_from_packs_dir(str(content_item.path)), features_a),
                (get_relative_path_from_packs_dir(str(duplicate.path)), features_b),
            )
            if features is None
        ]
        if unrestricted:
            # By far the most common failure: an item with no supportedFeatures
            # is supported everywhere, so it necessarily overlaps every other
            # variant of the same ID and can never coexist with one.
            return (
                f"{' and '.join(unrestricted)} declare(s) no 'supportedFeatures' and is "
                "therefore supported everywhere, so it overlaps every other item "
                "sharing this ID. Give each variant a 'supportedFeatures' value "
                "whose regions do not overlap, or change one of the IDs."
            )
        return (
            f"Their 'supportedFeatures' ({self._fmt(features_a)} and "
            f"{self._fmt(features_b)}) resolve to overlapping regions. Note that "
            "different feature names still collide when they are enabled in the "
            "same region."
        )

    @staticmethod
    def _fmt(features: Optional[FrozenSet[str]]) -> str:
        return ", ".join(sorted(features)) if features else "none"
