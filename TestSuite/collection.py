from pathlib import Path
from typing import Optional

from TestSuite.yml import YAML, yaml


class Collection(YAML):
    def __init__(self, tmpdir: Path, name: str, repo):
        # Create directory for the collection
        self._tmpdir_collection_path = tmpdir / name
        self._tmpdir_collection_path.mkdir(exist_ok=True)

        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        self.path = str(self._tmpdir_collection_path)

        super().__init__(
            tmp_path=self._tmpdir_collection_path / f"{self.name}.yml",
            repo_path=str(repo.path),
        )

    def build(
        self,
        yml: Optional[dict] = None,
    ):
        """Writes not None objects to files."""
        if yml is not None:
            self.write_dict(yml)

    def create_default_collection(
        self,
        name: str = "sample_collection",
        collection_id: str = "sample_collection_id",
    ):
        """Creates a new collection with basic data.

        Args:
            name: The name of the new collection, default is "sample_collection".
            collection_id: The ID of the new collection, default is "sample_collection_id".
        """
        default_collection_dir = Path(__file__).parent / "assets" / "default_collection"
        with open(default_collection_dir / "collection-sample.yml") as yml_file:
            yml = yaml.load(yml_file)
            yml["commonfields"]["id"] = collection_id
            yml["name"] = name
            self.build(yml=yml)
