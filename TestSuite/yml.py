from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.handlers import YAML_Handler
from TestSuite.file import File

yaml = YAML_Handler()


class YAML(File):
    def __init__(self, tmp_path: Path, repo_path: str, yml: Optional[dict] = None):
        super().__init__(tmp_path, repo_path)
        if yml:
            self.write_dict(yml)

    def write_dict(self, yml: dict):
        with open(self._tmp_path, "w+") as f:
            yaml.dump(yml, f)
            f.flush()

    def read_dict(self):
        return yaml.load(self._tmp_path.open())

    def update(self, update_obj: dict, key_dict_to_update: str = None):
        yml_contents = self.read_dict()
        if key_dict_to_update:
            if key_dict_to_update in yml_contents:
                yml_contents.get(key_dict_to_update).update(update_obj)
            else:
                yml_contents[key_dict_to_update] = update_obj
        else:
            yml_contents.update(update_obj)
        self.write_dict(yml_contents)

    def delete_key(self, key: str):
        yml_contents = self.read_dict()
        if key in yml_contents:
            del yml_contents[key]
            self.write_dict(yml_contents)

    def update_description(self, description: str):
        self.update({"description": description})
