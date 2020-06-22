from pathlib import Path
from typing import Optional

from ruamel import yaml
from TestSuite.file import File


class YAML(File):
    def __init__(self, tmp_path: Path, repo_path: str, yml: Optional[dict] = None):
        if yml is None:
            yml = ''
        else:
            yml = yaml.dump(yml)
        super().__init__(tmp_path, repo_path, yml)

    def write_dict(self, yml: dict):
        super().write(str(yaml.dump(yml)))

    def update(self, update_obj: dict):
        yml_contents = yaml.load(self.read())
        yml_contents.update(update_obj)
        self.write_dict(yml_contents)

    def update_description(self, description: str):
        self.update({'description': description})
