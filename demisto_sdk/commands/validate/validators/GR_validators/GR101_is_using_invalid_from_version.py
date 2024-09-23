from __future__ import annotations

from abc import ABC
from typing import Iterable, List, Union

from demisto_sdk.commands.common.tools import get_all_content_objects_paths_in_dir
from demisto_sdk.commands.content_graph.objects import (
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
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
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
    CaseField,
    CaseLayout,
    CaseLayoutRule,
]


class IsUsingInvalidFromVersionValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR101"
    description = "Validates that source's fromversion >= target's fromversion."
    rationale = "Content items should only use content items which have an equal or smaller fromversion."
    error_message = (
        "Content item '{0}' whose from_version is '{1}' is using content items:"
        " {2} whose from_version is higher (must be equal to, or less than ..)"
    )
    related_field = ""
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool = False
    ) -> List[ValidationResult]:
        file_paths_to_validate = (
            []
            if validate_all_files
            else get_all_content_objects_paths_in_dir(
                str(content_item.path) for content_item in content_items
            )
        )

        invalid_content_items = self.graph.find_uses_paths_with_invalid_fromversion(
            file_paths=file_paths_to_validate, for_supported_versions=True
        )
        final_validation_results = []
        for content_item in invalid_content_items:
            used_content_items = [
                relationship.content_item_to.object_id
                for relationship in content_item.uses
            ]
            final_validation_results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        content_item.name,
                        content_item.fromversion,
                        ", ".join(f"'{name}'" for name in used_content_items),
                    ),
                    content_object=content_item,
                )
            )

        return final_validation_results
