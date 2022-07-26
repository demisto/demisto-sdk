from pathlib import Path

from TestSuite.yml import YAML


class ParsingRule(YAML):
    def __init__(
        self,
        name: str,
        parsing_rule_dir_path: Path,
        repo_path: Path,
        yml_content: dict = {},
    ):
        self.parsing_rule_tmp_path = parsing_rule_dir_path / f'{name}.yml'
        self.name = name

        super().__init__(
            self.parsing_rule_tmp_path, str(repo_path), yml_content
        )

        if not yml_content:
            self.create_default_parsing_rule()

    def create_default_parsing_rule(self):
        self.write_dict(
            {
                'id': self.name,
                'name': self.name,
            }
        )
