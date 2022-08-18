from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.content_graph.constants import (
    ContentTypes,
    Rel,
    PACK_METADATA_FILENAME,
    RelationshipData
)
from demisto_sdk.commands.content_graph.parsers.parser_factory import ParserFactory
from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.parsers.classifier_mapper import ClassifierMapperParser
    from demisto_sdk.commands.content_graph.parsers.correlation_rule import CorrelationRuleParser
    from demisto_sdk.commands.content_graph.parsers.dashboard import DashboardParser
    from demisto_sdk.commands.content_graph.parsers.generic_definition import GenericDefinitionParser
    from demisto_sdk.commands.content_graph.parsers.generic_module import GenericModuleParser
    from demisto_sdk.commands.content_graph.parsers.generic_type import GenericTypeParser
    from demisto_sdk.commands.content_graph.parsers.incident_field import IncidentFieldParser
    from demisto_sdk.commands.content_graph.parsers.incident_type import IncidentTypeParser
    from demisto_sdk.commands.content_graph.parsers.indicator_field import IndicatorFieldParser
    from demisto_sdk.commands.content_graph.parsers.indicator_type import IndicatorTypeParser
    from demisto_sdk.commands.content_graph.parsers.integration import IntegrationParser
    from demisto_sdk.commands.content_graph.parsers.job import JobParser
    from demisto_sdk.commands.content_graph.parsers.layout import LayoutParser
    from demisto_sdk.commands.content_graph.parsers.list import ListParser
    from demisto_sdk.commands.content_graph.parsers.modeling_rule import ModelingRuleParser
    from demisto_sdk.commands.content_graph.parsers.parsing_rule import ParsingRuleParser
    from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser
    from demisto_sdk.commands.content_graph.parsers.report import ReportParser
    from demisto_sdk.commands.content_graph.parsers.script import ScriptParser
    from demisto_sdk.commands.content_graph.parsers.test_playbook import TestPlaybookParser
    from demisto_sdk.commands.content_graph.parsers.trigger import TriggerParser
    from demisto_sdk.commands.content_graph.parsers.widget import WidgetParser
    from demisto_sdk.commands.content_graph.parsers.wizard import WizardParser
    from demisto_sdk.commands.content_graph.parsers.xsiam_dashboard import XSIAMDashboardParser
    from demisto_sdk.commands.content_graph.parsers.xsiam_report import XSIAMReportParser

class PackContentItems:
    def __init__(self) -> None:
        self.classifier: List['ClassifierMapperParser'] = []
        self.correlation_rule: List['CorrelationRuleParser'] = []
        self.dashboard: List['DashboardParser'] = []
        self.generic_definition: List['GenericDefinitionParser'] = []
        self.generic_module: List['GenericModuleParser'] = []
        self.generic_type: List['GenericTypeParser'] = []
        self.incident_field: List['IncidentFieldParser'] = []
        self.incident_type: List['IncidentTypeParser'] = []
        self.indicator_field: List['IndicatorFieldParser'] = []
        self.indicator_type: List['IndicatorTypeParser'] = []
        self.integration: List['IntegrationParser'] = []
        self.job: List['JobParser'] = []
        self.layout: List['LayoutParser'] = []
        self.list_object: List['ListParser'] = []
        self.mapper: List['ClassifierMapperParser'] = []
        self.modeling_rule: List['ModelingRuleParser'] = []
        self.parsing_rule: List['ParsingRuleParser'] = []
        self.playbook: List['PlaybookParser'] = []
        self.report: List['ReportParser'] = []
        self.script: List['ScriptParser'] = []
        self.test_playbook: List['TestPlaybookParser'] = []
        self.trigger: List['TriggerParser'] = []
        self.widget: List['WidgetParser'] = []
        self.wizard: List['WizardParser'] = []
        self.xsiam_dashboard: List['XSIAMDashboardParser'] = []
        self.xsiam_report: List['XSIAMReportParser'] = []


class PackMetadataParser:
    def __init__(self, metadata: Dict[str, Any]) -> None:
        self.name: str = metadata['name']
        self.description: str = metadata['description']
        self.created: str = metadata.get('created', '')
        self.updated: str = metadata.get('updated', '')
        self.support: str = metadata['support']
        self.email: str = metadata.get('email', '')
        self.url: str = metadata['url']
        self.author: str = metadata['author']
        self.certification: str = 'certified' if self.support.lower() in ['xsoar', 'partner'] else ''
        self.hidden: bool = metadata.get('hidden', False)
        self.server_min_version: str = metadata.get('serverMinVersion', '')
        self.current_version: str = metadata['currentVersion']
        self.tags: List[str] = metadata['tags']
        self.categories: List[str] = metadata['categories']
        self.use_cases: List[str] = metadata['useCases']
        self.keywords: List[str] = metadata['keywords']
        self.price: Optional[int] = metadata.get('price')
        self.premium: Optional[bool] = metadata.get('premium')
        self.vendor_id: Optional[str] = metadata.get('vendorId')
        self.vendor_name: Optional[str] = metadata.get('vendorName')
        self.preview_only: Optional[bool] = metadata.get('previewOnly')


class PackParser(BaseContentParser, PackMetadataParser):
    def __init__(self, path: Path) -> None:
        BaseContentParser.__init__(self, path)
        metadata: Dict[str, Any] = get_json(path / PACK_METADATA_FILENAME)
        PackMetadataParser.__init__(self, metadata)
        print(f'Parsing {self.content_type} {self.object_id}')
        self.marketplaces = metadata.get('marketplaces', [])
        self.content_items: PackContentItems = PackContentItems()
        self.relationships: Dict[Rel, List[RelationshipData]] = {}
        self.parse_pack_folders()

    @property
    def object_id(self) -> str:
        return self.path.name

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.PACK

    def parse_pack_folders(self) -> None:
        for folder_path in ContentTypes.pack_folders(self.path):
            for content_item_path in folder_path.iterdir():  # todo: consider multiprocessing
                if content_item := ParserFactory.from_path(content_item_path, self):
                    content_item.add_to_pack()
