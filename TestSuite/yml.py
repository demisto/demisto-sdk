from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.xsoar_yaml import XSOAR_YAML

xsoar_yaml = XSOAR_YAML()

from TestSuite.file import File


class YML(File):
    def __init__(self, tmp_path: Path, repo_path: str, yml: Optional[dict] = None):
        if yml is None:
            init_yml = ''
        else:
            init_yml = xsoar_yaml.dump(yml)
        super().__init__(tmp_path, repo_path, init_yml)

    def write_dict(self, yml: dict):
        self.write(xsoar_yaml.dump(yml))

    def read_dict(self):
        return xsoar_yaml.load(self.read())

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
