from pathlib import Path

from TestSuite.yml import YAML


class ModelingRule(YAML):
    def __init__(
        self,
        name: str,
        modeling_rule_dir_path: Path,
        repo_path: Path,
        yml_content: dict = {},
    ):
        self.modeling_rule_tmp_path = modeling_rule_dir_path / f'{name}.yml'
        self.name = name

        super().__init__(
            self.modeling_rule_tmp_path, str(repo_path), yml_content
        )

        if not yml_content:
            self.create_default_modeling_rule()

    def create_default_modeling_rule(self):
        self.write_dict(
            {
                'id': self.name,
                'name': self.name,
            }
        )
