from pathlib import Path
from typing import TYPE_CHECKING, List

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.parsers.pack import PackParser


class IncidentTypeParser(JSONContentItemParser):
    def __init__(self, path: Path, pack: 'PackParser') -> None:
        super().__init__(path, pack)
        print(f'Parsing {self.content_type} {self.object_id}')
        self.playbook: str = self.json_data.get('playbookId')
        self.hours: int = self.json_data.get('hours')
        self.days: int = self.json_data.get('days')
        self.weeks: int = self.json_data.get('weeks')
        self.closure_script: str = self.json_data.get('closureScript')
        self.reputation_script_name: str = self.json_data.get('reputationScriptName')
        self.enhancement_script_names: List[str] = self.json_data.get('enhancementScriptNames')

        self.connect_to_dependencies()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.INCIDENT_TYPE

    def connect_to_dependencies(self) -> None:
        if pre_processing_script := self.json_data.get('preProcessingScript'):
            self.add_dependency(pre_processing_script, ContentTypes.SCRIPT)

        if playbook := self.json_data.get('playbookId'):
            self.add_dependency(playbook, ContentTypes.PLAYBOOK)

        if layout := self.json_data.get('layout'):
            self.add_dependency(layout, ContentTypes.LAYOUT)

    def add_to_pack(self) -> None:
        self.pack.content_items.incident_type.append(self)
