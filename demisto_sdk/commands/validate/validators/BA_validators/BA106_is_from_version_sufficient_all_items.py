from __future__ import annotations

from typing import Dict, Iterable, List, Union

from packaging.version import Version

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.assets_modeling_rule import (
    AssetsModelingRule,
)
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
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
from demisto_sdk.commands.content_graph.objects.job import Job
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.layout_rule import LayoutRule
from demisto_sdk.commands.content_graph.objects.list import List as LIST
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.pre_process_rule import PreProcessRule
from demisto_sdk.commands.content_graph.objects.report import Report
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport
from demisto_sdk.commands.validate.validators.BA_validators.BA106_is_from_version_sufficient import (
    IsFromVersionSufficientValidator,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[
    GenericDefinition,
    GenericField,
    GenericModule,
    GenericType,
    LIST,
    Mapper,
    Classifier,
    Widget,
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
    XSIAMDashboard,
    XSIAMReport,
    IncidentField,
    AssetsModelingRule,
    LayoutRule,
]

FROM_VERSION_DICT: Dict[ContentType, str] = {
    ContentType.ASSETS_MODELING_RULE: "6.2.1",
    ContentType.XSIAM_REPORT: "6.10.0",
    ContentType.INCIDENT_FIELD: "5.0.0",
    ContentType.INDICATOR_FIELD: "5.0.0",
    ContentType.CORRELATION_RULE: "6.10.0",
    ContentType.PARSING_RULE: "6.10.0",
    ContentType.LAYOUT_RULE: "6.10.0",
    ContentType.XSIAM_DASHBOARD: "6.10.0",
    ContentType.SCRIPT: "5.0.0",
    ContentType.PLAYBOOK: "5.0.0",
    ContentType.REPORT: "5.0.0",
    ContentType.WIZARD: "6.8.0",
    ContentType.JOB: "6.8.0",
    ContentType.LAYOUT: "6.0.0",
    ContentType.PREPROCESS_RULE: "6.8.0",
    ContentType.GENERIC_DEFINITION: "6.5.0",
    ContentType.GENERIC_MODULE: "6.5.0",
    ContentType.GENERIC_FIELD: "6.5.0",
    ContentType.GENERIC_TYPE: "6.5.0",
    ContentType.LIST: "6.5.0",
    ContentType.MAPPER: "6.0.0",
    ContentType.CLASSIFIER: "6.0.0",
    ContentType.WIDGET: "5.0.0",
    ContentType.DASHBOARD: "5.0.0",
    ContentType.INCIDENT_TYPE: "5.0.0",
}


class IsFromVersionSufficientAllItemsValidator(
    IsFromVersionSufficientValidator, BaseValidator[ContentTypes]
):
    """
    This class is for cases where the IsFromVersionSufficientValidator need to run on items that are not dependent on the item's type.
    """

    description = "Validate that the item's fromversion field is sufficient."
    error_message = "The {0} from version field is either missing or insufficient, need at least {1}, current is {2}."

    def is_valid(self, content_items: Iterable[ContentItem]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.content_type,
                    FROM_VERSION_DICT[content_item.content_type],
                    content_item.fromversion,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if Version(content_item.fromversion)
            < Version(FROM_VERSION_DICT[content_item.content_type])
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        version_to_set: str = FROM_VERSION_DICT[content_item.content_type]
        content_item.fromversion = version_to_set
        return FixResult(
            validator=self,
            message=self.fix_message.format(version_to_set),
            content_object=content_item,
        )
