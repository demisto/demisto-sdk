
from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import PACKS_FOLDER
from demisto_sdk.commands.common.tools import get_pack_name
from demisto_sdk.commands.content_graph.objects.assets_modeling_rule import (
    AssetsModelingRule,
)
from demisto_sdk.commands.content_graph.objects.base_playbook import BasePlaybook
from demisto_sdk.commands.content_graph.objects.base_script import BaseScript
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
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.job import Job
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.layout_rule import LayoutRule
from demisto_sdk.commands.content_graph.objects.list import List
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.pre_process_rule import PreProcessRule
from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData
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
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    GitStatuses,
    ValidationResult,
)

ContentTypes = Union[
    GenericDefinition,
    GenericField,
    GenericModule,
    GenericType,
    List,
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
    BasePlaybook,
    BaseScript,
    IndicatorType,
    Pack,
    TestPlaybook,
    TestScript,
    XDRCTemplate
]
class PackNameValidator(BaseValidator[ContentTypes]):
    error_code = "BA114"
    description = "Validate that the name of the pack for a content item was not changed."
    error_message = "Pack name for a content item with path {0} was changed from {1} to {2}, please undo."
    related_field = "path"
    expected_git_statuses = [GitStatuses.RENAMED]
    new_pack_name = ''
    old_pack_name = ''
    new_path = ''
    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    self.new_path,
                    self.old_pack_name,
                    self.new_pack_name,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if self.pack_name_has_changed(content_item)
        ]
        
    def pack_name_has_changed(self, content_item: ContentTypes):
        old_pack_name = get_pack_name(content_item.old_base_content_object.path)
        new_pack_name = get_pack_name(content_item.path)
        name_has_changed = new_pack_name != old_pack_name
        if name_has_changed:
            self.new_pack_name = new_pack_name
            self.old_pack_name = old_pack_name
            self.new_path = str(content_item.path).split(PACKS_FOLDER)[-1]
        return name_has_changed
            
