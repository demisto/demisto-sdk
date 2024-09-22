from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import ExecutionMode
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
from demisto_sdk.commands.validate.validators.GR_validators.GR101_is_using_invalid_from_version import (
    IsUsingInvalidFromVersionValidator,
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


class IsUsingInvalidFromVersionValidatorAllFiles(
    IsUsingInvalidFromVersionValidator, BaseValidator[ContentTypes]
):
    expected_execution_mode = [ExecutionMode.ALL_FILES]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph([], True)
