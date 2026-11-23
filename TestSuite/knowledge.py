from pathlib import Path
from typing import Optional

from TestSuite.yml import YAML, yaml


class Knowledge(YAML):
    def __init__(self, tmpdir: Path, name: str, repo):
        # Create directory for the knowledge
        self._tmpdir_knowledge_path = tmpdir / name
        self._tmpdir_knowledge_path.mkdir(exist_ok=True)

        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        self.path = str(self._tmpdir_knowledge_path)

        super().__init__(
            tmp_path=self._tmpdir_knowledge_path / f"{self.name}.yml",
            repo_path=str(repo.path),
        )

    def build(
        self,
        yml: Optional[dict] = None,
    ):
        """Writes not None objects to files."""
        if yml is not None:
            self.write_dict(yml)

    def create_default_knowledge(
        self,
        name: str = "sample_knowledge",
        knowledge_id: str = "sample_knowledge_id",
    ):
        """Creates a new knowledge with basic data.

        Args:
            name: The name of the new knowledge, default is "sample_knowledge".
            knowledge_id: The ID of the new knowledge, default is "sample_knowledge_id".
        """
        default_knowledge_dir = Path(__file__).parent / "assets" / "default_knowledge"
        with open(default_knowledge_dir / "knowledge-sample.yml") as yml_file:
            yml = yaml.load(yml_file)
            yml["commonfields"]["id"] = knowledge_id
            yml["name"] = name
            self.build(yml=yml)
