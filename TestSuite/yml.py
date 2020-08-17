from pathlib import Path
from typing import Optional

from ruamel import yaml
from TestSuite.file import File


class YAML(File):
    def __init__(self, tmp_path: Path, repo_path: str, yml: Optional[dict] = None):
        if yml is None:
            init_yml = ''
        else:
            init_yml = yaml.dump(yml)
        super().__init__(tmp_path, repo_path, init_yml)

    def write_dict(self, yml: dict):
        super().write(yaml.dump(yml))

    def read_dict(self):
        return yaml.safe_load(self.read())

    def update(self, update_obj: dict):
        yml_contents = self.read_dict()
        yml_contents.update(update_obj)
        self.write_dict(yml_contents)

    def update_description(self, description: str):
        self.update({'description': description})
