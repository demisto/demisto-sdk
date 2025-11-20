from pathlib import Path
from typing import Optional

from TestSuite.yml import YAML, yaml


class AgentixAction(YAML):
    def __init__(self, tmpdir: Path, name: str, repo):
        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        super().__init__(tmp_path=tmpdir / f"{self.name}.yml", repo_path=str(repo.path))

    @property
    def yml(self):
        # for backward compatible
        return self

    def build(
        self,
        yml: Optional[dict] = None,
    ):
        """Writes not None objects to files."""
        if yml is not None:
            self.write_dict(yml)

    def create_default_agentix_action(
        self,
        name: str = "sample_agentix_action",
        action_id: str = "sample_agentix_action_id",
    ):
        """Creates a new agentix action with basic data.
        Args:
            name: The name and ID of the new agentix action, default is "sample_agentix_action".
            action_id: The ID of the new agentix action, default is "sample_agentix_action_id".
        """
        default_agentix_action_dir = (
            Path(__file__).parent / "assets" / "default_agentix_action"
        )
        with open(default_agentix_action_dir / "agentix_action-sample.yml") as yml_file:
            yml = yaml.load(yml_file)
            yml["id"] = action_id
            yml["name"] = name
            self.build(yml=yml)

    def set_agentix_action_name(self, name: str):
        self.yml.update({"name": name})
