from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects import (
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
    Job,
    Layout,
    LayoutRule,
    Mapper,
    ModelingRule,
    Pack,
    ParsingRule,
    Playbook,
    PreProcessRule,
    Report,
    Widget,
    Wizard,
    XDRCTemplate,
    XSIAMDashboard,
    XSIAMReport,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.list import List as ListObject
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[
    Integration,
    Script,
    IncidentField,
    IndicatorField,
    IncidentType,
    GenericType,
    Classifier,
    Layout,
    LayoutRule,
    Playbook,
    CorrelationRule,
    Dashboard,
    GenericDefinition,
    GenericField,
    GenericModule,
    Job,
    ListObject,
    Mapper,
    ParsingRule,
    PreProcessRule,
    Report,
    Widget,
    Wizard,
    XDRCTemplate,
    XSIAMDashboard,
    XSIAMReport,
    IndicatorType,
    CaseField,
    CaseLayout,
    CaseLayoutRule,
    Pack,
    ModelingRule,
    AssetsModelingRule,
]


class SchemaValidator(BaseValidator[ContentTypes]):
    error_code = "ST110"
    description = (
        "Validate that the scheme's structure is valid, while excluding certain fields."
    )
    rationale = "Maintain valid structure for content items."

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message="\n".join(
                    str(error) for error in content_item.structure_errors
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if self.is_invalid_schema(content_item)
        ]

    def is_invalid_schema(self, content_item: ContentTypes) -> bool:
        return bool(content_item.structure_errors)
