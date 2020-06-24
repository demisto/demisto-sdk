import json
from pathlib import Path


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
        self._file_path.write_text(json.dumps(obj))

    def read_json_as_text(self) -> str:
        return self._file_path.read_text()

    def read_json_as_dict(self) -> dict:
        return json.loads(self._file_path.read_text())

    def append_to_json(self, obj: dict):
        file_content = self.read_json_as_dict()
        file_content.update(obj)
        self.write_json(file_content)
