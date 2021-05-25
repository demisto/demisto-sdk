from abc import abstractmethod
from typing import List, Set, Dict, Optional

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.layout.layout import LayoutObject
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.tools import (get_yaml)
from demisto_sdk.commands.convert.converters.abstract_converter import AbstractConverter


class LayoutBaseConverter(AbstractConverter):

    def __init__(self, pack: Pack):
        super().__init__()
        self.pack = pack

    @abstractmethod
    def convert_dir(self):
        pass

    def get_layouts_by_layout_type(self, layout_type: FileType) -> List[LayoutObject]:
        """
        Returns all layouts in the given pack whom layout type matches the 'layout_type' argument given.
        Args:
            layout_type (FileType): The layout type.

        Returns:
            (List[LayoutObject]): List of layouts whom type matches 'layout_type'.
        """
        return [layout for layout in self.pack.layouts if layout.type() == layout_type and layout.layout_id()]

    @staticmethod
    def get_layout_dynamic_fields() -> Set[str]:
        """
        Calculates all the indicator fields in the layouts container schema.
        Returns:
            (Set[str]): Set of all of the indicator field names in the layouts container schema.
        """
        schema_data: dict = get_yaml(
            '/Users/tneeman/dev/demisto/demisto-sdk/demisto_sdk/commands/common/schemas/layoutscontainer.yml')
        schema_mapping = schema_data.get('mapping', dict())
        return {schema_field for schema_field, schema_value in schema_mapping.items() if 'mapping' in schema_value}

    @staticmethod
    def create_layout_dict(layout_id: Optional[str] = None, type_id: Optional[str] = None,
                           from_version: Optional[str] = None, to_version: Optional[str] = None,
                           kind: Optional[str] = None) -> Dict:
        dict_with_maybe_none_values = dict(fromVersion=from_version, toVersion=to_version, name=layout_id, id=layout_id,
                                           version=-1, typeId=type_id, kind=kind)
        return {k: v for k, v in dict_with_maybe_none_values.items() if v is not None}
