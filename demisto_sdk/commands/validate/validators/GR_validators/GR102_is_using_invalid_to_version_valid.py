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
    CaseField,
    CaseLayout,
    CaseLayoutRule,
]


class IsUsingInvalidToVersionValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR102"
    description = "Validates that content items are not used in other content items which have a lower toversion."
    rationale = (
        "Prevent issues where used objects are not available due to a version mismatch."
    )
    error_message = (
        "Content item '{0}' whose to_version is '{1}' is using content items:"
        " {2} whose to_version is lower than {3}, making them incompatible"
    )
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

        invalid_content_items = self.graph.find_uses_paths_with_invalid_toversion(
            file_paths=file_paths_to_validate, for_supported_versions=True
        )
        result = []
        for content_item in invalid_content_items:
            used_content_items = [
                relationship.content_item_to.object_id
                for relationship in content_item.uses
            ]
            result.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        content_item.name,
                        content_item.toversion,
                        ", ".join(f"'{name}'" for name in used_content_items),
                        content_item.toversion,
                    ),
                    content_object=content_item,
                )
            )

        return result
