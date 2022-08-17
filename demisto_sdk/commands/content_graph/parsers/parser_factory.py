from pathlib import Path
from typing import Dict, List, Optional, Type

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser, NotAContentItem
from demisto_sdk.commands.content_graph.parsers.incident_field import IncidentFieldParser
from demisto_sdk.commands.content_graph.parsers.incident_type import IncidentTypeParser
from demisto_sdk.commands.content_graph.parsers.indicator_field import IndicatorFieldParser
from demisto_sdk.commands.content_graph.parsers.indicator_type import IndicatorTypeParser
from demisto_sdk.commands.content_graph.parsers.integration import IntegrationParser
from demisto_sdk.commands.content_graph.parsers.script import ScriptParser
from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser
from demisto_sdk.commands.content_graph.parsers.classifier_mapper import ClassifierMapperParser
from demisto_sdk.commands.content_graph.constants import ContentTypes


CONTENT_TYPE_TO_PARSER: Dict[str, Type[ContentItemParser]] = {
    ContentTypes.INTEGRATION: IntegrationParser,
    ContentTypes.SCRIPT: ScriptParser,
    ContentTypes.PLAYBOOK: PlaybookParser,
    ContentTypes.CLASSIFIER: ClassifierMapperParser,
    ContentTypes.INCIDENT_FIELD: IncidentFieldParser,
    ContentTypes.INCIDENT_TYPE: IncidentTypeParser,
    ContentTypes.INDICATOR_FIELD: IndicatorFieldParser,
    ContentTypes.INDICATOR_TYPE: IndicatorTypeParser,
}


class ParserFactory:
    @staticmethod
    def from_path(path: Path, pack_marketplaces: List[MarketplaceVersions]) -> Optional[ContentItemParser]:
        if not ContentItemParser.is_content_item(path):
            return None
        
        content_type: ContentTypes = ContentTypes.by_folder(path.parts[-2])
        if parser := CONTENT_TYPE_TO_PARSER.get(content_type):
            try:
                return parser(path, pack_marketplaces)
            except NotAContentItem:  # as e:
                # during the parsing we detected this is not a content item
                # print(str(e))
                pass
        return None
