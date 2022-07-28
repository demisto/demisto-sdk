from typing import Any, Dict

from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser
from demisto_sdk.commands.content_graph.constants import ContentTypes


class CommandParser(BaseContentParser):
    def __init__(self, cmd_data: Dict[str, Any], is_integration_deprecated: bool = False) -> None:
        self.cmd_data: Dict[str, Any] = cmd_data
        self.name: str = self.cmd_data.get('name')
        self.is_integration_deprecated: bool = is_integration_deprecated

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.COMMAND
    
    @property
    def node_id(self) -> str:
        return f'{self.content_type}:{self.name}'

    @property
    def deprecated(self) -> bool:
        return self.cmd_data.get('deprecated', False) or self.is_integration_deprecated

    def get_data(self) -> Dict[str, Any]:
        return {
            'node_id': self.node_id,
            'name': self.name,
            'deprecated': self.deprecated,
        }

