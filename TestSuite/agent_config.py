from pathlib import Path

from TestSuite.json_based import JSONBased


class AgentConfig(JSONBased):
    def __init__(self, name: str, agent_config_dir_path: Path, json_content: dict = {}):
        self.agent_config_tmp_path = agent_config_dir_path / f"{name}.json"
        self.name = name

        super().__init__(agent_config_dir_path, name, '')

        if json_content:
            self.write_json(json_content)
        else:
            self.create_default_agent_config()

    def create_default_agent_config(self):
        self.write_json({
            "content_global_id": self.name,
            "name": self.name,
            "os_type": "os_type_test",
            "profile_type": "profile_type_test",
            "yaml_template": 'yaml_test'
        })
