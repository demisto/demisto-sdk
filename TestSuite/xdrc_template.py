from pathlib import Path

from demisto_sdk.commands.common.handlers import YAML_Handler
from TestSuite.json_based import JSONBased

yaml = YAML_Handler()


class XDRCTemplate(JSONBased):
    def __init__(
        self,
        name: str,
        xdrc_template_dir_path: Path,
        json_content: dict = None,
        yaml_content: dict = None,
    ):
        self.xdrc_template_tmp_path = xdrc_template_dir_path / f"{name}.json"
        self.xdrc_template_yml_tmp_path = xdrc_template_dir_path / f"{name}.yml"
        self.name = name

        self._tmp_path = self.xdrc_template_yml_tmp_path
        self.write_dict(
            yaml_content
        ) if yaml_content else self.create_default_xdrc_template_yaml()

        self._tmp_path = self.xdrc_template_tmp_path
        super().__init__(xdrc_template_dir_path, name, "", json_content)

    def write_dict(self, yml: dict):
        yaml.dump(yml, self._tmp_path.open("w+"))

    def create_default(self):
        self.write_json(
            {
                "id": self.id,
                "name": self.id,
                "os_type": "os_type_test",
                "profile_type": "profile_type_test",
                "from_xdr_version": "3.5.0",
                "yaml_template": "",
            }
        )

    def create_default_xdrc_template_yaml(self):
        self.write_dict({"test": "xdrc template yaml test"})
