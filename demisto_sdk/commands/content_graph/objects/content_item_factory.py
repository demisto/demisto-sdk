from pathlib import Path
from typing import List, Type, Any, Dict
from demisto_sdk.commands.common.constants import MarketplaceVersions

import demisto_sdk.commands.content_graph.objects.content_item as content_item
import demisto_sdk.commands.content_graph.objects.incident_field as incident_field
import demisto_sdk.commands.content_graph.objects.incident_type as incident_type
import demisto_sdk.commands.content_graph.objects.indicator_field as indicator_field
import demisto_sdk.commands.content_graph.objects.indicator_type as indicator_type
import demisto_sdk.commands.content_graph.objects.integration as integration
import demisto_sdk.commands.content_graph.objects.script as script
import demisto_sdk.commands.content_graph.objects.playbook as playbook
import demisto_sdk.commands.content_graph.objects.classifier_mapper as classifier_mapper
from demisto_sdk.commands.content_graph.constants import ContentTypes, NodeData

CONTENT_TYPE_TO_CLASS: Dict[str, Type[content_item.ContentItem]] = {
    ContentTypes.INTEGRATION: integration.Integration,
    ContentTypes.SCRIPT: script.Script,
    ContentTypes.PLAYBOOK: playbook.Playbook,
    ContentTypes.CLASSIFIER: classifier_mapper.ClassifierMapper,
    ContentTypes.INCIDENT_FIELD: incident_field.IncidentField,
    ContentTypes.INCIDENT_TYPE: incident_type.IncidentType,
    ContentTypes.INDICATOR_FIELD: indicator_field.IndicatorField,
    ContentTypes.INDICATOR_TYPE: indicator_type.IndicatorType,
}


class ContentItemFactory:
    @staticmethod
    def from_database(nodes_data: List[NodeData]) -> Any:
        # todo
        return None
        
    @staticmethod
    def from_path(path: Path, pack_marketplaces: List[MarketplaceVersions]) -> Any:
        if not content_item.ContentItem.is_content_item(path):
            return None
        
        content_type: ContentTypes = ContentTypes.by_folder(path.parts[-2])
        if class_name := CONTENT_TYPE_TO_CLASS.get(content_type):
            try:
                return class_name(
                    path=path,
                    pack_marketplaces=pack_marketplaces,
                )
            except content_item.NotAContentItem:  # as e:
                # during the parsing we detected this is not a content item
                # print(str(e))
                pass
        return None
