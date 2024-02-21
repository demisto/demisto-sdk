from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.generic_definition import (
    GenericDefinition,
)
from demisto_sdk.commands.content_graph.objects.generic_field import GenericField
from demisto_sdk.commands.content_graph.objects.generic_module import GenericModule
from demisto_sdk.commands.content_graph.objects.generic_type import GenericType
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
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
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[
    Classifier,
    CorrelationRule,
    Dashboard,
    GenericDefinition,
    GenericField,
    GenericModule,
    GenericType,
    IncidentType,
    IndicatorField,
    Integration,
    Layout,
    LayoutRule,
    Mapper,
    ModelingRule,
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
]


class IsContentItemNameContainTrailingSpacesValidator(BaseValidator[ContentTypes]):
    error_code = "BA113"
    description = "Validator to check if content item names contain trailing spaces."
    error_message = "The following fields have a trailing spaces: {0} \nContent item fields can not have trailing spaces."
    fix_message = (
        "Removed trailing spaces from the following content item {0} fields: '{1}'."
    )
    related_field = "name, commonfields.id"
    is_auto_fixable = True
    invalid_fields: ClassVar[Dict[str, List[str]]] = {}
    fields_to_check = {"object_id": "id", "name": "name"}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_fields)),
                content_object=content_item,
            )
            for content_item in content_items
            if bool(invalid_fields := self.get_invalid_fields(content_item))
        ]

    def get_invalid_fields(self, content_item: ContentTypes) -> List[str]:
        self.invalid_fields[content_item.name] = [
            self.fields_to_check[field_name]
            for field_name, field_value in (
                (field, getattr(content_item, field))
                for field in self.fields_to_check.keys()
            )
            if field_value != field_value.rstrip()
        ]
        return self.invalid_fields[content_item.name]

    def fix(self, content_item: ContentTypes) -> FixResult:
        changed_fields = []
        for field in self.fields_to_check:
            field_value = getattr(content_item, field)
            if field in self.invalid_fields[content_item.name]:
                setattr(content_item, field, field_value.rstrip())
                changed_fields.append(self.fields_to_check[field])
        return FixResult(
            validator=self,
            content_object=content_item,
            message=self.fix_message.format(
                content_item.name, ", ".join(changed_fields)
            ),
        )
