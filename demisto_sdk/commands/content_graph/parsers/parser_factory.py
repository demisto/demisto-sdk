from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser, NotAContentItem
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

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.parsers.pack import PackParser


CONTENT_TYPE_TO_PARSER: Dict[ContentTypes, Type[ContentItemParser]] = {
    ContentTypes.CLASSIFIER: ClassifierMapperParser,
    # ContentTypes.CORRELATION_RULE: CorrelationRuleParser,
    # ContentTypes.DASHBOARD: DashboardParser,
    # ContentTypes.GENERIC_DEFINITION: GenericDefinitionParser,
    # ContentTypes.GENERIC_MODULE: GenericModuleParser,
    # ContentTypes.GENERIC_TYPE: GenericTypeParser,
    ContentTypes.INCIDENT_FIELD: IncidentFieldParser,
    ContentTypes.INCIDENT_TYPE: IncidentTypeParser,
    ContentTypes.INDICATOR_FIELD: IndicatorFieldParser,
    ContentTypes.INDICATOR_TYPE: IndicatorTypeParser,
    ContentTypes.INTEGRATION: IntegrationParser,
    # ContentTypes.JOB: JobParser,
    # ContentTypes.LAYOUT: LayoutParser,
    # ContentTypes.LIST: ListParser,
    # ContentTypes.MODELING_RULE: ModelingRuleParser,
    # ContentTypes.PARSING_RULE: ParsingRuleParser,
    ContentTypes.PLAYBOOK: PlaybookParser,
    # ContentTypes.REPORT: ReportParser,
    ContentTypes.SCRIPT: ScriptParser,
    # ContentTypes.TEST_PLAYBOOK: TestPlaybookParser,
    # ContentTypes.TRIGGER: TriggerParser,
    # ContentTypes.WIDGET: WidgetParser,
    # ContentTypes.WIZARD: WizardParser,
    # ContentTypes.XSIAM_DASHBOARD: XSIAMDashboardParser,
    # ContentTypes.XSIAM_REPORT: XSIAMReportParser,
}


class ParserFactory:
    @staticmethod
    def from_path(path: Path, pack: 'PackParser') -> Optional[ContentItemParser]:
        if not ContentItemParser.is_content_item(path):
            return None
        
        content_type: ContentTypes = ContentTypes.by_folder(path.parts[-2])
        if parser := CONTENT_TYPE_TO_PARSER.get(content_type):
            try:
                return parser(path, pack)
            except NotAContentItem:  # as e:
                # during the parsing we detected this is not a content item
                # print(str(e))
                pass
        return None
