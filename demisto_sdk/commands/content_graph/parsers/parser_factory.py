from pathlib import Path
from typing import List, Type, Any

import demisto_sdk.commands.content_graph.parsers.content_item as content_item
import demisto_sdk.commands.content_graph.parsers.integration as integration
import demisto_sdk.commands.content_graph.parsers.script as script
import demisto_sdk.commands.content_graph.parsers.playbook as playbook
from demisto_sdk.commands.content_graph.constants import ContentTypes

CONTENT_TYPE_TO_PARSER: Type[content_item.ContentItemParser] = {
    ContentTypes.INTEGRATION: integration.IntegrationParser,
    ContentTypes.SCRIPT: script.ScriptParser,
    ContentTypes.PLAYBOOK: playbook.PlaybookParser,
}


class ParserFactory:
    @staticmethod
    def from_path(path: Path, pack_marketplaces: List[str]) -> Any:
        if not content_item.ContentItemParser.is_content_item(path):
            return None
        
        content_type: ContentTypes = ContentTypes.by_folder(path.parts[-2])
        if parser := CONTENT_TYPE_TO_PARSER.get(content_type):
            try:
                return parser(path, pack_marketplaces)
            except content_item.NotAContentItem:
                # during the parsing we detected this is not a content item
                pass
        return None
