from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class IncidentTypeParser(JSONContentItemParser, content_type=ContentTypes.INCIDENT_TYPE):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.playbook: str = self.json_data.get('playbookId')
        self.hours: int = self.json_data.get('hours')
        self.days: int = self.json_data.get('days')
        self.weeks: int = self.json_data.get('weeks')
        self.closure_script: str = self.json_data.get('closureScript') or None

        self.connect_to_dependencies()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.INCIDENT_TYPE

    def connect_to_dependencies(self) -> None:
        """ Collects the script, playbook and layout used by the incident type as mandatory dependencies.
        """
        if pre_processing_script := self.json_data.get('preProcessingScript'):
            self.add_dependency(pre_processing_script, ContentTypes.SCRIPT)

        if playbook := self.json_data.get('playbookId'):
            self.add_dependency(playbook, ContentTypes.PLAYBOOK)

        if layout := self.json_data.get('layout'):
            self.add_dependency(layout, ContentTypes.LAYOUT)
