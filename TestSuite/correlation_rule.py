from pathlib import Path

from TestSuite.yml import YAML


class CorrelationRule(YAML):
    def __init__(
        self,
        name: str,
        correlation_rule_dir_path: Path,
        repo_path: Path,
        yml_content: dict = None,
    ):
        self.correlation_rule_tmp_path = correlation_rule_dir_path / f"{name}.yml"
        self.name = name

        super().__init__(self.correlation_rule_tmp_path, str(repo_path), yml_content)

        if not yml_content:
            self.create_default_correlation_rule()

    def create_default_correlation_rule(self):
        self.write_dict(
            {
                "global_rule_id": self.name,
                "name": self.name,
                "fromversion": "6.10.0"
            }
        )
