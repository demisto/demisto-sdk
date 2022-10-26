from pathlib import Path

from demisto_sdk.commands.common.handlers import YAML_Handler
from TestSuite.json_based import JSONBased

yaml = YAML_Handler()


class XDRCTemplate(JSONBased):
    def __init__(self, name: str, agent_config_dir_path: Path, json_content: dict = None, yaml_content: dict = None):
        self.agent_config_tmp_path = agent_config_dir_path / f"{name}.json"
        self.agent_config_yml_tmp_path = agent_config_dir_path / f"{name}.yml"
        self.name = name

        self._tmp_path = self.agent_config_yml_tmp_path
        self.write_dict(yaml_content) if yaml_content else self.create_default_agent_config_yaml()

        self._tmp_path = self.agent_config_tmp_path
        super().__init__(agent_config_dir_path, name, '')
        self.write_json(json_content) if json_content else self.create_default_agent_config_json()

    def write_dict(self, yml: dict):
        yaml.dump(yml, self._tmp_path.open('w+'))

    def create_default_agent_config_json(self):
        self.write_json({
            "content_global_id": self.name,
            "name": self.name,
            "os_type": "os_type_test",
            "profile_type": "profile_type_test",
            "yaml_template": ''
        })

    def create_default_agent_config_yaml(self):
        self.write_dict({
            'test': 'agent config yaml test'
        })
