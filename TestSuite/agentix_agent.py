from pathlib import Path
from typing import Optional

from TestSuite.yml import YAML, yaml


class AgentixAgent(YAML):
    def __init__(self, tmpdir: Path, name: str, repo):
        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        self.path = str(tmpdir)
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

    def create_default_agentix_agent(
        self,
        name: str = "sample_agentix_agent",
        agent_id: str = "sample_agentix_agent_id",
    ):
        """Creates a new agentix agent with basic data.
        Args:
            name: The name of the new agentix agent, default is "sample_agentix_agent".
            agent_id: The ID of the new agentix agent, default is "sample_agentix_agent_id".
        """
        default_agentix_agent_dir = (
            Path(__file__).parent / "assets" / "default_agentix_agent"
        )
        with open(default_agentix_agent_dir / "agentix_agent-sample.yml") as yml_file:
            yml = yaml.load(yml_file)
            yml["id"] = agent_id
            yml["name"] = name
            self.build(yml=yml)
