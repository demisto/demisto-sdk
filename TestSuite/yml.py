from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.handlers import YAML_Handler
from TestSuite.file import File

yaml = YAML_Handler()


class YAML(File):
    def __init__(self, tmp_path: Path, repo_path: str, yml: Optional[dict] = None):
        if yml:
            self.write_dict(yml)
        super().__init__(tmp_path, repo_path)

    def write_dict(self, yml: dict):
        yaml.dump(yml, self._tmp_path.open('w+'))

    def read_dict(self):
        return yaml.load(self._tmp_path.open())

    def update(self, update_obj: dict):
        yml_contents = self.read_dict()
        yml_contents.update(update_obj)
        self.write_dict(yml_contents)

    def delete_key(self, key: str):
        yml_contents = self.read_dict()
        if key in yml_contents:
            del yml_contents[key]
            self.write_dict(yml_contents)

    def update_description(self, description: str):
        self.update({'description': description})
