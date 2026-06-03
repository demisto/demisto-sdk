from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.handlers import JSON_Handler
from TestSuite.file import File

json = JSON_Handler()


class AgentixSkill:
    """A TestSuite representation of an AgentixSkill content item.

    Each skill lives in its own folder under ``AgentixSkills/`` and contains
    two files: ``metadata.json`` (schema fields) and ``skill.md`` (the body).
    """

    def __init__(self, tmpdir: Path, name: str, repo):
        # Create directory for the skill
        self._tmpdir_skill_path = tmpdir / name
        self._tmpdir_skill_path.mkdir(exist_ok=True)

        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        self.path = str(self._tmpdir_skill_path)

        # metadata.json (the schema)
        self._metadata_path = self._tmpdir_skill_path / "metadata.json"
        self.metadata_file = File(self._metadata_path, str(repo.path), txt="{}")

        # skill.md (the body)
        self.skill_content_file = File(
            self._tmpdir_skill_path / "skill.md", str(repo.path)
        )

    @property
    def metadata_path(self) -> str:
        return str(self._metadata_path)

    def write_metadata(self, metadata: dict) -> None:
        """Write the metadata.json content."""
        self.metadata_file.write(json.dumps(metadata))

    def read_metadata(self) -> dict:
        """Read the metadata.json content as a dict."""
        return json.loads(self.metadata_file.read())

    def build(
        self,
        metadata: Optional[dict] = None,
        skill_content: Optional[str] = None,
    ):
        """Writes any not-None objects to files."""
        if metadata is not None:
            self.write_metadata(metadata)
        if skill_content is not None:
            self.skill_content_file.write(skill_content)

    def create_default_agentix_skill(
        self,
        name: str = "sample_agentix_skill",
        skill_id: str = "sample_agentix_skill_id",
        skill_content: str = "Sample skill body.",
    ):
        """Create a new agentix skill with basic data.

        Args:
            name: Skill name (default ``"sample_agentix_skill"``).
            skill_id: Skill ID (default ``"sample_agentix_skill_id"``).
            skill_content: The skill body (Markdown). Default ``"Sample skill body."``.
        """
        default_dir = Path(__file__).parent / "assets" / "default_agentix_skill"
        with open(default_dir / "metadata.json") as fh:
            metadata = json.load(fh)
        metadata["id"] = skill_id
        metadata["name"] = name
        metadata.setdefault("display", name)
        self.build(metadata=metadata, skill_content=skill_content)

    def update(self, update_obj: dict):
        """Update the metadata.json content, handling ``content`` specially.

        If ``content`` is present, write it to ``skill.md`` instead of the JSON file.
        """
        if "content" in update_obj:
            content = update_obj.pop("content")
            if content is not None:
                self.skill_content_file.write(content)

        if update_obj:
            metadata = self.read_metadata()
            metadata.update(update_obj)
            self.write_metadata(metadata)
