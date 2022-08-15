from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.objects.content_item import JSONContentItem


class IncidentType(JSONContentItem):
    def __post_init__(self) -> None:
        if self.should_parse_object:
            self.content_type = ContentTypes.INCIDENT_TYPE
            print(f'Parsing {self.content_type} {self.object_id}')

            self.connect_to_dependencies()

    def connect_to_dependencies(self) -> None:
        if pre_processing_script := self.json_data.get('preProcessingScript'):
            self.add_dependency(pre_processing_script, ContentTypes.SCRIPT)

        if playbook := self.json_data.get('playbookId'):
            self.add_dependency(playbook, ContentTypes.PLAYBOOK)

        if layout := self.json_data.get('layout'):
            self.add_dependency(layout, ContentTypes.LAYOUT)
