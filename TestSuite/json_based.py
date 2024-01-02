import os
import re
from pathlib import Path
from typing import Union

from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.handlers import JSON_Handler
from TestSuite.test_suite_base import TestSuiteBase

json = JSON_Handler()


class JSONBased(TestSuiteBase):
    def __init__(self, dir_path: Path, name: str, prefix: str, json_content: dict = None):
        self._dir_path = dir_path
        if prefix:
            self.name = f'{prefix.rstrip("-")}-{name}.json'
        else:
            self.name = f"{name}.json"

        self._file_path = dir_path / self.name
        self.path = str(self._file_path)
        super().__init__(self._file_path)
        
        if json_content:
            self.write_json(json_content)
        else:
            self.create_default()
    
    def create_default(self):
        # to be override by sub classes
        self.write_json({})
    
    def write_json(self, obj: dict):
        self._file_path.write_text(json.dumps(obj), None)

    def write_as_text(self, content: str):
        self._file_path.write_text(content, None)

    def get_path_from_pack(self):
        dir_parts = str(self._file_path).split("/")
        dir_from_packs = PACKS_DIR
        add_directory = False
        for directory in dir_parts:
            if add_directory:
                dir_from_packs = os.path.join(dir_from_packs, directory)
            elif directory == PACKS_DIR:
                add_directory = True

        return dir_from_packs

    def read_json_as_text(self) -> str:
        return self._file_path.read_text()

    def read_json_as_dict(self) -> dict:
        with self._file_path.open() as f:
            return json.load(f)

    def update(self, obj: dict):
        file_content = self.read_json_as_dict()
        file_content.update(obj)
        self.write_json(file_content)

    def remove(self, key: str):
        file_content = self.read_json_as_dict()
        file_content.pop(key, None)
        self.write_json(file_content)

    def _set_field_by_path(self, path_to_field: str, new_val: str = None):
        """Inner method to remove, add or update a given field.

        Args:
            path_to_field (str): The path to field to remove.
                Ex: alerts_filter.filter.AND.[0].SEARCH_FIELD

            new_val (str): The field's new value. If not provided, removes the field.
        """

        def get_index_or_key(k) -> Union[str, int]:
            list_index_pattern = r"\[([0-9]+)\]"
            if idx_match := re.match(list_index_pattern, k):
                return int(idx_match[1])
            return k

        splitted_path = path_to_field.split(".")
        data = pointer = self.read_json_as_dict()
        try:
            for idx, k in enumerate(splitted_path):
                if idx == len(splitted_path) - 1:
                    if not new_val:
                        del pointer[get_index_or_key(k)]
                    else:
                        pointer[get_index_or_key(k)] = new_val
                    self.update(data)
                else:
                    pointer = pointer[get_index_or_key(k)]
        except Exception:
            path = ".".join(splitted_path[: idx - 1])
            raise Exception(f"Invalid path: {k} does not exist under {path}")

    def remove_field_by_path(self, path_to_field: str):
        """Removes an inner field by dot notation.
        If the path to field does not exist, raises an error.

        Args:
            path_to_field (str): The path to field to remove.
                Ex: alerts_filter.filter.AND.[0].SEARCH_FIELD
        """
        self._set_field_by_path(path_to_field)

    def add_or_update_field_by_path(self, path_to_field: str, val: str):
        """Adds or updates an inner field by dot notation.
        If the path to field does not exist, raises an error.

        Args:
            path_to_field (str): The path to field to set.
                Ex: alerts_filter.filter.AND.[0].SEARCH_FIELD

            val (str): The field's expected value.
        """
        self._set_field_by_path(path_to_field, val)
