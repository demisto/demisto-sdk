from __future__ import annotations

from typing import Dict, Iterable, List, Union

from ordered_set import OrderedSet

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.case_layout import CaseLayout
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Layout, CaseLayout]

INVALID_SECTIONS: List = [
    "evidence",
    "childInv",
    "linkedIncidents",
    "team",
    "droppedIncidents",
    "todoTasks",
]

INVALID_TABS: List = ["evidenceBoard", "relatedIncidents"]


class IsValidTypeValidator(BaseValidator[ContentTypes]):
    error_code = "LO107"
    description = "Ensures that only supported types are used in the layout for XSIAM compatibility."
    rationale = "Limited by the platform."
    error_message = "The following invalid types were found in the layout: {0}. Those types are not supported in XSIAM, remove them or change the layout to be XSOAR only."
    related_field = "tabs.sections.type, tabs.type"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validator_results: List[ValidationResult] = []
        for content_item in content_items:
            if (
                MarketplaceVersions.MarketplaceV2.value in content_item.marketplaces
                and (invalid_types := self.get_invalid_layout_type(content_item))
            ):
                validator_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(", ".join(invalid_types)),
                        content_object=content_item,
                    )
                )
        return validator_results

    def get_invalid_layout_type(self, content_item: ContentTypes) -> List[str]:
        invalid_types_contained: List = []
        tabs: List[Dict] = content_item.data.get("detailsV2", {}).get("tabs") or [{}]
        for tab in tabs:
            if (tab_type := tab.get("type")) in INVALID_TABS:
                invalid_types_contained.append(tab_type)
            sections: List[Dict] = tab.get("sections", [{}])
            for section in sections:
                if (section_type := section.get("type")) in INVALID_SECTIONS:
                    invalid_types_contained.append(section_type)
        return list(OrderedSet(invalid_types_contained))
