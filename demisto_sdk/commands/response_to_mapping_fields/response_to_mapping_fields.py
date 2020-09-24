import json
import os
import sys
from typing import Any, Optional, Union

from demisto_sdk.commands.common.tools import LOG_COLORS, print_color


class ResponseToMappingFields:
    def __init__(self):
        self._found_none_type = False

    def run(self, input_path: str, output_path: Optional[str] = None):
        if not os.path.isfile(input_path):
            print_color(f'File {input_path} does not exists.', LOG_COLORS.RED)
            sys.exit(1)
        if not output_path:
            output_path = os.path.join(os.getcwd(), f'{os.path.splitext(input_path)[0]}_out.json')
        dct = json.load(open(input_path))
        updated = self._create_scheme(dct)
        if self._found_none_type:
            print_color('Found NoneType, Find and replace in the output', LOG_COLORS.YELLOW)
            self._found_none_type = False
        json.dump(updated, open(output_path, 'w+'), indent=4)
        print_color(f'A JSON scheme was written to {output_path}', LOG_COLORS.GREEN)

    def _create_scheme(self, obj: Any) -> Union[dict, list, str]:
        """
        If a dictionary is given:
            map key: type of value
        If a list:
            will run build_list function
        else:
            type(obj).__name__

        Args:
            obj: A object to map

        Returns:
            Union[dict, list, str]: Scheme of given response
        """
        if isinstance(obj, dict):
            return {key: self._create_scheme(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return self._build_list(obj)
        if obj is None:
            self._found_none_type = True
        return type(obj).__name__

    def _build_list(self, items: list) -> Any:
        """
        Return a scheme of given list.

        If items is List[dict]:
            returns unified dict on all items.
        if empty list:
            returns []
        else:
            returns create_scheme on one item.

        Args:
            items: A list to map to scheme

        Returns:
            Scheme of the list.
        """
        dct = dict()
        if not items:
            return 'list'
        if isinstance(items[0], dict):
            for item in items:
                for key, value in item.items():
                    dct[key] = self._create_scheme(value)
        else:
            # Validate all the same value type
            return self._create_scheme(items[0])
        return dct if dct else []
