from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional

from demisto_sdk.commands.content_graph.constants import ContentTypes, Nodes, Relationships
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.generic_definition import GenericDefinition
from demisto_sdk.commands.content_graph.objects.generic_module import GenericModule
from demisto_sdk.commands.content_graph.objects.generic_type import GenericType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.job import Job
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.list import List as ListObject
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


class PackContentItems(BaseModel):
    classifier: List[Classifier] = Field([], alias=ContentTypes.CLASSIFIER.value)
    correlation_rule: List[CorrelationRule] = Field([], alias=ContentTypes.CORRELATION_RULE.value)
    dashboard: List[Dashboard] = Field([], alias=ContentTypes.DASHBOARD.value)
    generic_definition: List[GenericDefinition] = Field([], alias=ContentTypes.GENERIC_DEFINITION.value)
    generic_module: List[GenericModule] = Field([], alias=ContentTypes.GENERIC_MODULE.value)
    generic_type: List[GenericType] = Field([], alias=ContentTypes.GENERIC_TYPE.value)
    incident_field: List[IncidentField] = Field([], alias=ContentTypes.INCIDENT_FIELD.value)
    incident_type: List[IncidentType] = Field([], alias=ContentTypes.INCIDENT_TYPE.value)
    indicator_field: List[IndicatorField] = Field([], alias=ContentTypes.INDICATOR_FIELD.value)
    indicator_type: List[IndicatorType] = Field([], alias=ContentTypes.INDICATOR_TYPE.value)
    integration: List[Integration] = Field([], alias=ContentTypes.INTEGRATION.value)
    job: List[Job] = Field([], alias=ContentTypes.JOB.value)
    layout: List[Layout] = Field([], alias=ContentTypes.LAYOUT.value)
    list: List[ListObject] = Field([], alias=ContentTypes.LIST.value)
    mapper: List[Mapper] = Field([], alias=ContentTypes.MAPPER.value)
    modeling_rule: List[ModelingRule] = Field([], alias=ContentTypes.MODELING_RULE.value)
    parsing_rule: List[ParsingRule] = Field([], alias=ContentTypes.PARSING_RULE.value)
    playbook: List[Playbook] = Field([], alias=ContentTypes.PLAYBOOK.value)
    report: List[Report] = Field([], alias=ContentTypes.REPORT.value)
    script: List[Script] = Field([], alias=ContentTypes.SCRIPT.value)
    test_playbook: List[TestPlaybook] = Field([], alias=ContentTypes.TEST_PLAYBOOK.value)
    trigger: List[Trigger] = Field([], alias=ContentTypes.TRIGGER.value)
    widget: List[Widget] = Field([], alias=ContentTypes.WIDGET.value)
    wizard: List[Wizard] = Field([], alias=ContentTypes.WIZARD.value)
    xsiam_dashboard: List[XSIAMDashboard] = Field([], alias=ContentTypes.XSIAM_DASHBOARD.value)
    xsiam_report: List[XSIAMReport] = Field([], alias=ContentTypes.XSIAM_REPORT.value)

    def __iter__(self):
        for content_items in vars(self).values():
            for content_item in content_items:
                yield content_item

    class Config:
        arbitrary_types_allowed = True
        orm_mode = True
        allow_population_by_field_name = True


class PackMetadata(BaseModel):
    name: str
    description: str
    created: str
    updated: str
    support: str
    email: str
    url: str
    author: str
    certification: str
    hidden: bool
    server_min_version: str = Field(alias='serverMinVersion')
    current_version: str = Field(alias='currentVersion')
    tags: List[str]
    categories: List[str]
    use_cases: List[str] = Field(alias='useCases')
    keywords: List[str]
    price: Optional[int] = None
    premium: Optional[bool] = None
    vendor_id: Optional[str] = Field(None, alias='vendorId')
    vendor_name: Optional[str] = Field(None, alias='vendorName')
    preview_only: Optional[bool] = Field(None, alias='previewOnly')

    class Config:
        arbitrary_types_allowed = True
        orm_mode = True


class Pack(BaseContent, PackMetadata):
    path: Path
    object_id: str
    content_type: ContentTypes
    node_id: str
    content_items: PackContentItems = Field(alias='contentItems', exclude=True)
    relationships: Relationships = Field(Relationships(), exclude=True)

    def dump(path: Path):
        pass
    
    def to_nodes(self) -> Nodes:
        return Nodes(self.to_dict(), *[content_item.to_dict() for content_item in self.content_items])
