from typing import Union
from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.validate.validators.ST_validators.ST110_is_valid_scheme import SchemaValidator
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
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import StructureError
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

class StrictSchemaValidator(SchemaValidator):
    error_code = "ST111"
    description = "Validate that the scheme's structure is valid, no fields excluded."
    rationale = "Maintain valid structure for content items."
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.ADDED]

    def is_invalid_schema(self, content_item: ContentTypes) -> bool:
        return bool(content_item.structure_errors)