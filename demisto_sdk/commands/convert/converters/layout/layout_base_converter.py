import os
from abc import abstractmethod
from typing import Any, Dict, Optional

from demisto_sdk.commands.common.constants import (FileType)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.commands.convert.converters.base_converter import \
    BaseConverter


class LayoutBaseConverter(BaseConverter):
    DEFAULT_SCHEMA_PATH = os.path.normpath(os.path.join(__file__, '..', '..', '..', '..', 'common/schemas/',
                                                        f'{FileType.LAYOUTS_CONTAINER.value}.yml'))

    def __init__(self, pack: Pack):
        super().__init__()
        self.pack = pack

    @abstractmethod
    def convert_dir(self) -> int:
        pass

    @staticmethod
    def get_layout_dynamic_fields(schema_path: str = DEFAULT_SCHEMA_PATH) -> Dict[str, Any]:
        """
        Calculates all the indicator fields in the layouts container schema.
        Args:
            schema_path (str): Path to the layouts container schema.
        Returns:
            (Dict[str, Any]): Dict of all of the dynamic field names and their value in the layouts container schema.
        """
        schema_data: dict = get_yaml(schema_path)
        schema_mapping = schema_data.get('mapping', dict())
        return {schema_field: schema_value for schema_field, schema_value in schema_mapping.items()
                if 'mapping' in schema_value}

    @staticmethod
    def create_layout_dict(layout_id: Optional[str] = None, type_id: Optional[str] = None,
                           from_version: Optional[str] = None, to_version: Optional[str] = None,
                           kind: Optional[str] = None) -> Dict:
        """
        Receives optional fields for creating a dict representing fields in layout dict.
        Args:
            layout_id (Optional[str]): Layout ID.
            type_id  (Optional[str]): Type ID of the layout. Relevant for layouts below 6.0.0.
            from_version (Optional[str]): From version.
            to_version (Optional[str]): To version.
            kind (Optional[str]): Layout kind. Relevant for layouts below 6.0.0

        Returns:
            (Dict) Dict object with the requested fields.
        """
        dict_with_maybe_none_values = dict(fromVersion=from_version, toVersion=to_version, name=layout_id, id=layout_id,
                                           version=-1, typeId=type_id, kind=kind)
        return {k: v for k, v in dict_with_maybe_none_values.items() if v is not None}
