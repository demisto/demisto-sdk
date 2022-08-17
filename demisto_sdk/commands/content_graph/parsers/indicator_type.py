from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class IndicatorTypeParser(JSONContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[MarketplaceVersions]) -> None:
        super().__init__(path, pack_marketplaces)
        print(f'Parsing {self.content_type} {self.object_id}')
        self.connect_to_dependencies()
        self.regex = self.json_data.get('regex')
        self.reputation_script_names = self.json_data.get('reputationScriptName')
        self.enhancement_script_names = self.json_data.get('enhancementScriptNames')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.INDICATOR_TYPE

    @property
    def name(self) -> str:
        return self.json_data.get('details')

    @property
    def description(self) -> str:
        return self.json_data.get('details')

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