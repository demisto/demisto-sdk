from typing import Any, Dict, Generator, List

from more_itertools import map_reduce
from pydantic import BaseModel, ConfigDict, Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.assets_modeling_rule import (
    AssetsModelingRule,
)
from demisto_sdk.commands.content_graph.objects.case_field import CaseField
from demisto_sdk.commands.content_graph.objects.case_layout import CaseLayout
from demisto_sdk.commands.content_graph.objects.case_layout_rule import CaseLayoutRule
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
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
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
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.objects.test_script import TestScript
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.content_graph.objects.xdrc_template import XDRCTemplate
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport


class PackContentItems(BaseModel):
    # The alias is for marshalling purposes
    case_field: List[CaseField] = Field([], alias=ContentType.CASE_FIELD.value)  # type: ignore[literal-required]
    case_layout: List[CaseLayout] = Field([], alias=ContentType.CASE_LAYOUT.value)  # type: ignore[literal-required]
    case_layout_rule: List[CaseLayoutRule] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.CASE_LAYOUT_RULE.value,
    )
    classifier: List[Classifier] = Field([], alias=ContentType.CLASSIFIER.value)  # type: ignore[literal-required]
    correlation_rule: List[CorrelationRule] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.CORRELATION_RULE.value,
    )
    dashboard: List[Dashboard] = Field([], alias=ContentType.DASHBOARD.value)  # type: ignore[literal-required]
    generic_definition: List[GenericDefinition] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.GENERIC_DEFINITION.value,
    )
    generic_field: List[GenericField] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.GENERIC_FIELD.value,
    )
    generic_module: List[GenericModule] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.GENERIC_MODULE.value,
    )
    generic_type: List[GenericType] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.GENERIC_TYPE.value,
    )
    incident_field: List[IncidentField] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.INCIDENT_FIELD.value,
    )
    incident_type: List[IncidentType] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.INCIDENT_TYPE.value,
    )
    indicator_field: List[IndicatorField] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.INDICATOR_FIELD.value,
    )
    indicator_type: List[IndicatorType] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.INDICATOR_TYPE.value,
    )
    integration: List[Integration] = Field([], alias=ContentType.INTEGRATION.value)  # type: ignore[literal-required]
    job: List[Job] = Field([], alias=ContentType.JOB.value)  # type: ignore[literal-required]
    layout: List[Layout] = Field([], alias=ContentType.LAYOUT.value)  # type: ignore[literal-required]
    list: List[ListObject] = Field([], alias=ContentType.LIST.value)  # type: ignore[literal-required]
    mapper: List[Mapper] = Field([], alias=ContentType.MAPPER.value)  # type: ignore[literal-required]
    modeling_rule: List[ModelingRule] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.MODELING_RULE.value,
    )
    parsing_rule: List[ParsingRule] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.PARSING_RULE.value,
    )
    playbook: List[Playbook] = Field([], alias=ContentType.PLAYBOOK.value)  # type: ignore[literal-required]
    report: List[Report] = Field([], alias=ContentType.REPORT.value)  # type: ignore[literal-required]
    script: List[Script] = Field([], alias=ContentType.SCRIPT.value)  # type: ignore[literal-required]
    test_playbook: List[TestPlaybook] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.TEST_PLAYBOOK.value,
    )
    trigger: List[Trigger] = Field([], alias=ContentType.TRIGGER.value)  # type: ignore[literal-required]
    widget: List[Widget] = Field([], alias=ContentType.WIDGET.value)  # type: ignore[literal-required]
    wizard: List[Wizard] = Field([], alias=ContentType.WIZARD.value)  # type: ignore[literal-required]
    xsiam_dashboard: List[XSIAMDashboard] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.XSIAM_DASHBOARD.value,
    )
    xsiam_report: List[XSIAMReport] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.XSIAM_REPORT.value,
    )
    xdrc_template: List[XDRCTemplate] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.XDRC_TEMPLATE.value,
    )
    layout_rule: List[LayoutRule] = Field([], alias=ContentType.LAYOUT_RULE.value)  # type: ignore[literal-required]
    preprocess_rule: List[PreProcessRule] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.PREPROCESS_RULE.value,
    )
    test_script: List[TestScript] = Field([], alias=ContentType.TEST_SCRIPT.value)  # type: ignore[literal-required]
    assets_modeling_rule: List[AssetsModelingRule] = Field(  # type: ignore[literal-required]
        [],
        alias=ContentType.ASSETS_MODELING_RULE.value,
    )

    def __iter__(self) -> Generator[ContentItem, Any, Any]:  # type: ignore
        """Defines the iteration of the object. Each iteration yields a single content item."""
        for content_items in vars(self).values():
            yield from content_items

    def items_by_type(self) -> Dict[ContentType, List[ContentItem]]:
        return map_reduce(iter(self), lambda i: i.content_type)

    def __bool__(self) -> bool:
        """Used for easier determination of content items existence in a pack."""
        return bool(list(self))

    model_config = ConfigDict(
        arbitrary_types_allowed=True, from_attributes=True, populate_by_name=True
    )
