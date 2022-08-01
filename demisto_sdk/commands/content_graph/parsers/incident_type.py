from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class IncidentTypeParser(JSONContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        super().__init__(path, pack_marketplaces)
        print(f'Parsing {self.content_type} {self.content_item_id}')
        self.connect_to_dependencies()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.INCIDENT_TYPE

    def connect_to_dependencies(self) -> None:
        if pre_processing_script := self.json_data.get('preProcessingScript'):
            self.add_dependency(pre_processing_script, ContentTypes.SCRIPT)

        if playbook := self.json_data.get('playbookId'):
            self.add_dependency(playbook, ContentTypes.PLAYBOOK)