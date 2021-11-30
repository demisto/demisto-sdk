import json
import os
from pathlib import Path

from demisto_sdk.commands.common.constants import PACKS_DIR


class JSONBased:
    def __init__(self, dir_path: Path, name: str, prefix: str):
        self._dir_path = dir_path
        if prefix:
            self.name = f'{prefix.rstrip("-")}-{name}.json'
        else:
            self.name = f'{name}.json'

        self._file_path = dir_path / self.name
        self.path = str(self._file_path)
        self.write_json({})

    def write_json(self, obj: dict):
        self._file_path.write_text(json.dumps(obj), None)

    def write_as_text(self, content: str):
        self._file_path.write_text(content, None)

    def get_path_from_pack(self):
        dir_parts = str(self._file_path).split('/')
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
        return json.loads(self._file_path.read_text())

    def update(self, obj: dict):
        file_content = self.read_json_as_dict()
        file_content.update(obj)
        self.write_json(file_content)

    def remove(self, key: str):
        file_content = self.read_json_as_dict()
        file_content.pop(key, None)
        self.write_json(file_content)
