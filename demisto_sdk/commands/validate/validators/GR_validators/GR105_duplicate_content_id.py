from __future__ import annotations

from abc import ABC
from typing import FrozenSet, Iterable, List, Optional, Set, Union

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.regional_rules import (
    REGIONAL_RULES_PATH,
    RegionalRules,
)
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
    error_message = "Duplicate ID '{0}' also found in {1}. {2} {3}"
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
        if rules is None:
            logger.info(
                f"[GR105] {REGIONAL_RULES_PATH} not found - region-aware duplicate "
                "handling is disabled, every duplicate ID will be reported."
            )

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
                            self._region_clause(colliding_regions),
                            self._explain(content_item, duplicate, colliding_regions),
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

        `None` means the pair is legal; an empty set means they collide but the
        regions could not be named.
        """
        if rules is None:
            # Without the rules file, features cannot be mapped to regions, so
            # non-overlap can never be proven. Fall back to the original,
            # region-unaware behaviour of reporting every duplicate.
            return set()

        features_a = get_content_item_supported_features(content_item)
        features_b = get_content_item_supported_features(duplicate)

        regions_a = rules.regions_for_features(features_a)
        regions_b = rules.regions_for_features(features_b)
        if not regions_a or not regions_b:
            # Neither side maps to a known region (no region blocks declared, or
            # the features are unknown), so we cannot prove they never overlap.
            # Report, as the pre-region-aware validator always did.
            return set()
        return (regions_a & regions_b) or None

    @staticmethod
    def _region_clause(colliding_regions: Set[str]) -> str:
        """States where the pair collides, or that this could not be determined.

        An empty set means the pair is reported because non-overlap could not be
        proven, not because they were found to share every region, so it must
        not be phrased as a known collision.
        """
        if not colliding_regions:
            return (
                "The region(s) in which both items are active could not be "
                "determined."
            )
        return (
            "Both items are active in the following region(s): "
            f"{', '.join(sorted(colliding_regions))}."
        )

    def _explain(
        self,
        content_item: ContentTypes,
        duplicate: ContentTypes,
        colliding_regions: Set[str],
    ) -> str:
        """Explains why the pair collides, in the author's terms."""
        features_a = get_content_item_supported_features(content_item)
        features_b = get_content_item_supported_features(duplicate)

        if not colliding_regions:
            # Reported because non-overlap could not be proven. Claiming an
            # overlap here would send the author looking for a conflict that
            # was never established.
            path_a = get_relative_path_from_packs_dir(str(content_item.path))
            path_b = get_relative_path_from_packs_dir(str(duplicate.path))
            return (
                "Their 'supportedFeatures' could not be resolved to any region "
                f"({path_a}: {self._fmt(features_a)}; {path_b}: "
                f"{self._fmt(features_b)}), so it cannot be proven that the two are "
                "never active together. Check that every feature name appears under "
                f"'supported_features' in {REGIONAL_RULES_PATH}, or change one of "
                "the IDs."
            )

        unrestricted = [
            path
            for path, features in (
                (get_relative_path_from_packs_dir(str(content_item.path)), features_a),
                (get_relative_path_from_packs_dir(str(duplicate.path)), features_b),
            )
            if features is None
        ]
        if unrestricted:
            # An item with no supportedFeatures is supported everywhere, so it
            # overlaps every other variant of the same ID.
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
        """Renders a resolved `supportedFeatures` value.

        An absent key and an explicit empty list are opposites - supported
        everywhere versus restricted to no region - so they must not read alike.
        """
        if features is None:
            return "not declared, so supported everywhere"
        if not features:
            return "declared empty, so active in no region"
        return ", ".join(sorted(features))
