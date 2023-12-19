from __future__ import annotations

from typing import Union

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


class IsFromVersionSufficientAllItemsValidator(
    IsFromVersionSufficientValidator, BaseValidator[ContentTypes]
):
    """
    This class is for cases where the IsFromVersionSufficientValidator need to run on items that are not dependent on the item's type.
    """
