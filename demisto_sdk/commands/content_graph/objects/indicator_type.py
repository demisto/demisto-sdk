from pathlib import Path
from typing import Any, Dict, List

from pydantic import Field

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.objects.content_item import JSONContentItem


class IndicatorType(JSONContentItem):
    regex: str = ''

    def __init__(self, **data) -> None:
        super().__init__(**data)
        if self.parsing_object:
            self.content_type = ContentTypes.INDICATOR_TYPE
            print(f'Parsing {self.content_type} {self.object_id}')
            self.node_id = self.get_node_id()
            self.regex = self.json_data.get('regex')

            self.connect_to_dependencies()

    def connect_to_dependencies(self) -> None:
        for field in ['reputationScriptName', 'enhancementScriptNames']:
            associated_scripts = self.json_data.get(field)
            if associated_scripts and associated_scripts != 'null':
                associated_scripts = [associated_scripts] if not isinstance(associated_scripts, list) else associated_scripts
                for script in associated_scripts:
                    self.add_dependency(script, ContentTypes.SCRIPT, is_mandatory=False)

        if reputation_command := self.json_data.get('reputationCommand'):
            self.add_dependency(reputation_command, ContentTypes.COMMAND, is_mandatory=False)

        if layout := self.json_data.get('layout'):
            self.add_dependency(layout, ContentTypes.LAYOUT)