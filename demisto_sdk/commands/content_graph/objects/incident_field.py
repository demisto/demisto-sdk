from pathlib import Path
from typing import Any, Dict, List

from pydantic import Field
from demisto_sdk.commands.common.tools import normalize_field_name

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.objects.content_item import JSONContentItem


class IncidentFieldParser(JSONContentItem):
    cli_name: str = Field('', alias='cliName')
    field_type: str = Field('', alias='type')
    associated_to_all: bool = Field(False, alias='associatedToAll')

    def __post_init__(self) -> None:
        self.content_type = self.content_type or ContentTypes.INCIDENT_FIELD
        self.item_id = normalize_field_name(self.item_id)
        self.node_id = self.node_id or f'{self.content_type}:{self.item_id}'
        self.cli_name = self.cli_name or self.json_data.get('cliName')
        self.field_type = self.field_type or self.json_data.get('type')
        self.associated_to_all = self.associated_to_all or self.json_data.get('associatedToAll')

        self.connect_to_dependencies()


    def connect_to_dependencies(self) -> None:
        for associated_type in set(self.json_data.get('associatedTypes') or []):
            self.add_dependency(associated_type, ContentTypes.INCIDENT_TYPE, is_mandatory=False)

        for system_associated_type in set(self.json_data.get('systemAssociatedTypes') or []):
            self.add_dependency(system_associated_type, ContentTypes.INCIDENT_TYPE, is_mandatory=False)

        if script := self.json_data.get('script'):
            self.add_dependency(script, ContentTypes.SCRIPT)

        if field_calc_script := self.json_data.get('fieldCalcScript'):
            self.add_dependency(field_calc_script, ContentTypes.SCRIPT)