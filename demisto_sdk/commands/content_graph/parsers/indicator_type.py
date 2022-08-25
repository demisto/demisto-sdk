from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.common import ContentTypes
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class IndicatorTypeParser(JSONContentItemParser, content_type=ContentTypes.INDICATOR_TYPE):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.connect_to_dependencies()
        self.regex: str = self.json_data.get('regex')
        self.reputation_script_name: str = self.json_data.get('reputationScriptName') or None
        self.enhancement_script_names: List[str] = self.json_data.get('enhancementScriptNames')

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
        """ Collects scripts and the reputation command used as optional dependencies,
        and the layout as a mandatory dependency.
        """
        for field in ['reputationScriptName', 'enhancementScriptNames']:
            associated_scripts = self.json_data.get(field)
            if associated_scripts and associated_scripts != 'null':
                associated_scripts = [associated_scripts] if not isinstance(associated_scripts, list) \
                    else associated_scripts
                for script in associated_scripts:
                    self.add_dependency(script, ContentTypes.SCRIPT, is_mandatory=False)

        if reputation_command := self.json_data.get('reputationCommand'):
            self.add_dependency(reputation_command, ContentTypes.COMMAND, is_mandatory=False)

        if layout := self.json_data.get('layout'):
            self.add_dependency(layout, ContentTypes.LAYOUT)
