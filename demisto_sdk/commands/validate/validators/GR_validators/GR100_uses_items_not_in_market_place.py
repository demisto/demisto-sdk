from __future__ import annotations

from abc import ABC
from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.common import RelationshipType
from demisto_sdk.commands.content_graph.objects import (
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
    Mapper,
    ModelingRule,
    Pack,
    ParsingRule,
    Playbook,
    Report,
    Script,
    TestPlaybook,
    Trigger,
    Widget,
    Wizard,
    XSIAMDashboard,
    XSIAMReport,
)
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
]


class MarketplacesFieldValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR100"
    description = (
        "Detect content items that attempt to use other content items which are not supported in all of the "
        "marketplaces of the content item."
    )
    rationale = "Content graph proper construction."
    error_message = (
        "Content item '{content_name}' can be used in the '{marketplaces}' marketplaces,"
        " however it uses content items: '{used_content_items}'"
        " which are not supported in all of the marketplaces of '{content_name}'."
    )

    related_field = "marketplaces"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files=False
    ) -> List[ValidationResult]:
        validation_results = []

        pack_ids_to_validate = (
            [item.pack_id for item in content_items] if not validate_all_files else []
        )

        # The content items that use content items with invalid marketplaces.
        invalid_content_items = self.graph.find_uses_paths_with_invalid_marketplaces(
            pack_ids_to_validate
        )
        for content_item in invalid_content_items:
            uses_content_items = [
                item.content_item_to.object_id
                for item in content_item.relationships_data.get(RelationshipType.USES)
            ]

            validation_results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        content_name=content_item.name,
                        marketplaces=", ".join(content_item.marketplaces),
                        used_content_items=", ".join(uses_content_items),
                    ),
                    content_object=content_item,
                )
            )
        return validation_results
