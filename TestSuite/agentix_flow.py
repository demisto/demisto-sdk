from pathlib import Path
from typing import Optional

from TestSuite.yml import YAML, yaml


class AgentixFlow(YAML):
    """A TestSuite representation of an AgentixFlow content item.

    Each flow lives in its own folder under ``AgentixFlows/`` and contains a
    single ``<FlowName>.yml`` file. Unlike the other Agentix types, a flow has a
    top-level ``id`` and ``version`` (no ``commonfields`` block) and a nested
    ``definition`` map.
    """

    def __init__(self, tmpdir: Path, name: str, repo):
        # Create directory for the flow
        self._tmpdir_flow_path = tmpdir / name
        self._tmpdir_flow_path.mkdir(exist_ok=True)

        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        self.path = str(self._tmpdir_flow_path)

        super().__init__(
            tmp_path=self._tmpdir_flow_path / f"{self.name}.yml",
            repo_path=str(repo.path),
        )

    def build(
        self,
        yml: Optional[dict] = None,
    ):
        """Writes not None objects to files."""
        if yml is not None:
            self.write_dict(yml)

    def create_default_agentix_flow(
        self,
        name: str = "Sample Agentix Flow",
        flow_id: str = "sample-agentix-flow",
    ):
        """Creates a new agentix flow with basic data.

        Args:
            name: The name of the new flow, default is "Sample Agentix Flow".
            flow_id: The ID of the new flow, default is "sample-agentix-flow".
        """
        default_flow_dir = Path(__file__).parent / "assets" / "default_agentix_flow"
        with open(default_flow_dir / "agentix_flow-sample.yml") as yml_file:
            yml = yaml.load(yml_file)
            yml["id"] = flow_id
            yml["name"] = name
            yml["definition"]["flow_id"] = flow_id
            self.build(yml=yml)
