from __future__ import annotations

from typing import Iterable, List, Union

from packaging.version import Version

from demisto_sdk.commands.content_graph.objects.assets_modeling_rule import (
    AssetsModelingRule,
)
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
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
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.job import Job
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.layout_rule import LayoutRule
from demisto_sdk.commands.content_graph.objects.list import List as ListObject
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.pre_process_rule import PreProcessRule
from demisto_sdk.commands.content_graph.objects.report import Report
from demisto_sdk.commands.content_graph.objects.script import Script
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
    GenericDefinition,
    GenericField,
    GenericModule,
    GenericType,
    ListObject,
    Mapper,
    Classifier,
    Widget,
    Integration,
    Dashboard,
    IncidentType,
    Script,
    Playbook,
    Report,
    Wizard,
    Job,
    Layout,
    PreProcessRule,
    CorrelationRule,
    ParsingRule,
    ModelingRule,
    XSIAMDashboard,
    Trigger,
    XSIAMReport,
    IncidentField,
    IndicatorField,
    AssetsModelingRule,
    LayoutRule,
]


class FromToVersionSyncedValidator(BaseValidator[ContentTypes]):
    error_code = "BA118"
    description = (
        "Validate that the item's toversion is greater/equal then its fromversion."
    )
    rationale = "Content with a from_version greater than to_version will not show in the platform."
    error_message = "The {0} fromversion and toversion are not synchronized.\nThe toversion ({1}) should be greater than the fromversion ({2})."
    related_field = "fromversion, toversion"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.content_type,
                    content_item.toversion,
                    content_item.fromversion,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if Version(content_item.toversion) <= Version(content_item.fromversion)
        ]
