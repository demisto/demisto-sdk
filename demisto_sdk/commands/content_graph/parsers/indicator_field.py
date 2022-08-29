from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class IndicatorFieldParser(JSONContentItemParser, content_type=ContentType.INDICATOR_FIELD):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.cli_name = self.json_data.get('cliName')
        self.type = self.json_data.get('type')
        self.associated_to_all = self.json_data.get('associatedToAll')

        self.connect_to_dependencies()

    @property
    def object_id(self) -> str:
        return self.json_data.get('cliName')
    
    def connect_to_dependencies(self) -> None:
        """ Collects indicator types used by the field as optional dependencies, and scripts as mandatory dependencies.
        """
        for associated_type in set(self.json_data.get('associatedTypes') or []):
            self.add_dependency(associated_type, ContentType.INDICATOR_TYPE, is_mandatory=False)

        for system_associated_type in set(self.json_data.get('systemAssociatedTypes') or []):
            self.add_dependency(system_associated_type, ContentType.INDICATOR_TYPE, is_mandatory=False)

        if script := self.json_data.get('script'):
            self.add_dependency(script, ContentType.SCRIPT)

        if field_calc_script := self.json_data.get('fieldCalcScript'):
            self.add_dependency(field_calc_script, ContentType.SCRIPT)
