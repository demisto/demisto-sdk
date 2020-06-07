import json
from pathlib import Path


class JSONBased:
    def __init__(self, dir_path: Path, name: str, prefix: str):
        self._dir_path = dir_path
        self.name = f'{prefix.rstrip("-")}-{name}.json'
        self._file_path = dir_path / self.name
        self.path = str(self._file_path)
        self.write_json({})

    def write_json(self, obj: dict):
        self._file_path.write_text(json.dumps(obj))
