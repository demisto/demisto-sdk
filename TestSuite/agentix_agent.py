from pathlib import Path
from typing import Optional

from TestSuite.file import File
from TestSuite.yml import YAML, yaml


class AgentixAgent(YAML):
    def __init__(self, tmpdir: Path, name: str, repo):
        # Create directory for the agent
        self._tmpdir_agent_path = tmpdir / name
        self._tmpdir_agent_path.mkdir(exist_ok=True)

        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        self.path = str(self._tmpdir_agent_path)

        super().__init__(
            tmp_path=self._tmpdir_agent_path / f"{self.name}.yml",
            repo_path=str(repo.path),
        )

        # Add system instructions file
        self.system_instructions = File(
            self._tmpdir_agent_path / f"{self.name}_systeminstructions.md",
            self._repo.path,
        )

    def build(
        self,
        yml: Optional[dict] = None,
        system_instructions: Optional[str] = None,
    ):
        """Writes not None objects to files."""
        if yml is not None:
            self.write_dict(yml)
        if system_instructions is not None:
            self.system_instructions.write(system_instructions)

    def create_default_agentix_agent(
        self,
        name: str = "sample_agentix_agent",
        agent_id: str = "sample_agentix_agent_id",
        system_instructions: str = "",
    ):
        """Creates a new agentix agent with basic data.
        Args:
            name: The name of the new agentix agent, default is "sample_agentix_agent".
            agent_id: The ID of the new agentix agent, default is "sample_agentix_agent_id".
            system_instructions: The system instructions content, default is empty string.
        """
        default_agentix_agent_dir = (
            Path(__file__).parent / "assets" / "default_agentix_agent"
        )
        with open(default_agentix_agent_dir / "agentix_agent-sample.yml") as yml_file:
            yml = yaml.load(yml_file)
            yml["id"] = agent_id
            yml["name"] = name
            self.build(yml=yml, system_instructions=system_instructions)

    def update(self, update_obj: dict, key_dict_to_update: Optional[str] = None):
        """Update the YAML content, handling systeminstructions specially."""
        # Extract systeminstructions if present and write to file
        if "systeminstructions" in update_obj:
            system_instructions = update_obj.pop("systeminstructions")
            if system_instructions:
                self.system_instructions.write(system_instructions)

        # Call parent update for remaining fields
        if update_obj:
            super().update(update_obj, key_dict_to_update)
