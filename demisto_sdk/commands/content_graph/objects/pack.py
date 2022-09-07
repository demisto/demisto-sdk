from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.content_graph.common import Nodes, Relationships
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.correlation_rule import \
    CorrelationRule
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.generic_definition import \
    GenericDefinition
from demisto_sdk.commands.content_graph.objects.generic_field import \
    GenericField
from demisto_sdk.commands.content_graph.objects.generic_module import \
    GenericModule
from demisto_sdk.commands.content_graph.objects.generic_type import GenericType
from demisto_sdk.commands.content_graph.objects.incident_field import \
    IncidentField
from demisto_sdk.commands.content_graph.objects.incident_type import \
    IncidentType
from demisto_sdk.commands.content_graph.objects.indicator_field import \
    IndicatorField
from demisto_sdk.commands.content_graph.objects.indicator_type import \
    IndicatorType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.job import Job
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.list import List as ListObject
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.modeling_rule import \
    ModelingRule
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.report import Report
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.test_playbook import \
    TestPlaybook
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import \
    XSIAMDashboard
from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport
from pydantic import BaseModel, Field


class PackContentItems(BaseModel):
    classifier: List[Classifier] = []
    correlation_rule: List[CorrelationRule] = []
    dashboard: List[Dashboard] = []
    generic_definition: List[GenericDefinition] = []
    generic_field: List[GenericField] = []
    generic_module: List[GenericModule] = []
    generic_type: List[GenericType] = []
    incident_field: List[IncidentField] = []
    incident_type: List[IncidentType] = []
    indicator_field: List[IndicatorField] = []
    indicator_type: List[IndicatorType] = []
    integration: List[Integration] = []
    job: List[Job] = []
    layout: List[Layout] = []
    list: List[ListObject] = []
    mapper: List[Mapper] = []
    modeling_rule: List[ModelingRule] = []
    parsing_rule: List[ParsingRule] = []
    playbook: List[Playbook] = []
    report: List[Report] = []
    script: List[Script] = []
    test_playbook: List[TestPlaybook] = []
    trigger: List[Trigger] = []
    widget: List[Widget] = []
    wizard: List[Wizard] = []
    xsiam_dashboard: List[XSIAMDashboard] = []
    xsiam_report: List[XSIAMReport] = []

    def __iter__(self):
        """ Defines the iteration of the object. Each iteration yields a single content item.
        """
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


class Pack(BaseContent, PackMetadata):
    path: Path
    contributors: Optional[List[str]] = None
    content_items: PackContentItems = Field(alias='contentItems', exclude=True)
    relationships: Relationships = Field(Relationships(), exclude=True)

    def to_nodes(self) -> Nodes:
        return Nodes(self.to_dict(), *[content_item.to_dict() for content_item in self.content_items])
