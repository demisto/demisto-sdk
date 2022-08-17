from pathlib import Path
from typing import Any, Dict, List
from demisto_sdk.commands.common.tools import normalize_field_name

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class IncidentFieldParser(JSONContentItemParser):
    def __init__(self) -> None:
        super().__init__()
        print(f'Parsing {self.content_type} {self.object_id}')
        self.cli_name = self.json_data.get('cliName')
        self.field_type = self.json_data.get('type')
        self.associated_to_all = self.json_data.get('associatedToAll')

        self.connect_to_dependencies()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.INDICATOR_FIELD

    @property
    def object_id(self) -> str:
        return self.cli_name

    def connect_to_dependencies(self) -> None:
        for associated_type in set(self.json_data.get('associatedTypes') or []):
            self.add_dependency(associated_type, ContentTypes.INCIDENT_TYPE, is_mandatory=False)

        for system_associated_type in set(self.json_data.get('systemAssociatedTypes') or []):
            self.add_dependency(system_associated_type, ContentTypes.INCIDENT_TYPE, is_mandatory=False)

        if script := self.json_data.get('script'):
            self.add_dependency(script, ContentTypes.SCRIPT)

        if field_calc_script := self.json_data.get('fieldCalcScript'):
            self.add_dependency(field_calc_script, ContentTypes.SCRIPT)
