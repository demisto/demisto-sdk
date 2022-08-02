from pathlib import Path
from typing import List, Type, Any

import demisto_sdk.commands.content_graph.parsers.content_item as content_item
import demisto_sdk.commands.content_graph.parsers.incident_field as incident_field
import demisto_sdk.commands.content_graph.parsers.incident_type as incident_type
import demisto_sdk.commands.content_graph.parsers.indicator_field as indicator_field
import demisto_sdk.commands.content_graph.parsers.indicator_type as indicator_type
import demisto_sdk.commands.content_graph.parsers.integration as integration
import demisto_sdk.commands.content_graph.parsers.script as script
import demisto_sdk.commands.content_graph.parsers.playbook as playbook
import demisto_sdk.commands.content_graph.parsers.classifier_mapper as classifier_mapper
from demisto_sdk.commands.content_graph.constants import ContentTypes

CONTENT_TYPE_TO_PARSER: Type[content_item.ContentItemParser] = {
    ContentTypes.INTEGRATION: integration.IntegrationParser,
    ContentTypes.SCRIPT: script.ScriptParser,
    ContentTypes.PLAYBOOK: playbook.PlaybookParser,
    ContentTypes.CLASSIFIER: classifier_mapper.ClassifierMapperParser,
    ContentTypes.INCIDENT_FIELD: incident_field.IncidentFieldParser,
    ContentTypes.INCIDENT_TYPE: incident_type.IncidentTypeParser,
    ContentTypes.INDICATOR_FIELD: indicator_field.IndicatorFieldParser,
    ContentTypes.INDICATOR_TYPE: indicator_type.IndicatorTypeParser,
}


class ParserFactory:
    @staticmethod
    def from_path(path: Path, pack_marketplaces: List[str]) -> Any:
        if not content_item.ContentItemParser.is_content_item(path):
            return None
        
        content_type: ContentTypes = ContentTypes.by_folder(path.parts[-2])
        # if content_type in [ContentTypes.CLASSIFIER, ContentTypes.INCIDENT_FIELD, ContentTypes.INDICATOR_FIELD, ContentTypes.INDICATOR_TYPE]:
        #     pass
        if parser := CONTENT_TYPE_TO_PARSER.get(content_type):
            try:
                return parser(path, pack_marketplaces)
            except content_item.NotAContentItem:  # as e:
                # during the parsing we detected this is not a content item
                # print(str(e))
                pass
        return None
