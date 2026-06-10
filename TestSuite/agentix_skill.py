from pathlib import Path
from typing import Optional

from TestSuite.file import File
from TestSuite.yml import YAML, yaml


class AgentixSkill(YAML):
    """A TestSuite representation of an AgentixSkill content item.

    Each skill lives in its own folder under ``AgentixSkills/`` and contains
    two files: ``<SkillName>.yml`` (schema fields, flat top-level YAML) and
    ``<SkillName>_skill.md`` (the body), both named after the skill folder.
    """

    SCHEMA_FILE_SUFFIX = ".yml"
    SKILL_BODY_FILE_SUFFIX = "_skill.md"

    def __init__(self, tmpdir: Path, name: str, repo):
        # Create directory for the skill
        self._tmpdir_skill_path = tmpdir / name
        self._tmpdir_skill_path.mkdir(exist_ok=True)

        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        self.path = str(self._tmpdir_skill_path)

        # File names share the skill folder name, like most YAML content items.
        self._schema_file_name = f"{name}{self.SCHEMA_FILE_SUFFIX}"
        self._skill_body_file_name = f"{name}{self.SKILL_BODY_FILE_SUFFIX}"

        # <SkillName>.yml (the schema) — initialise via the YAML mixin so
        # write_dict / update helpers from the base class work as for other YAML
        # content items (e.g. AgentixAgent).
        super().__init__(
            tmp_path=self._tmpdir_skill_path / self._schema_file_name,
            repo_path=str(repo.path),
        )

        # <SkillName>_skill.md (the body)
        self.skill_content_file = File(
            self._tmpdir_skill_path / self._skill_body_file_name, str(repo.path)
        )

    @property
    def metadata_path(self) -> str:
        return str(self._tmpdir_skill_path / self._schema_file_name)

    def write_metadata(self, metadata: dict) -> None:
        """Write the ``<SkillName>.yml`` content."""
        self.write_dict(metadata)

    def read_metadata(self) -> dict:
        """Read the ``<SkillName>.yml`` content as a dict."""
        return self.read_dict()

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
        name: str = "Sample Agentix Skill",
        skill_id: str = "sample-agentix-skill-id",
        skill_content: str = "Sample skill body.",
    ):
        """Create a new agentix skill with basic data.

        The default fixture lives under ``assets/default_agentix_skill/`` and
        uses a nested ``commonfields: {id, version}`` block symmetric with
        ``AgentixAgent``. Caller-supplied overrides update both
        ``commonfields.id`` (the authoritative source for the parser) and a
        top-level ``id`` (kept for parity with ``AgentixAgent``'s
        ``create_default_agentix_agent`` helper).

        ``AgentixSkill`` has no ``display`` field — ``name`` is the
        human-readable Title Case label shown to the user.

        Args:
            name: Skill name in Title Case (default ``"Sample Agentix Skill"``).
            skill_id: Skill ID in kebab-case (default ``"sample-agentix-skill-id"``).
            skill_content: The skill body (Markdown). Default ``"Sample skill body."``.
        """
        default_dir = Path(__file__).parent / "assets" / "default_agentix_skill"
        with open(default_dir / "skill.yml") as fh:
            metadata = yaml.load(fh)
        metadata.setdefault("commonfields", {"version": -1})
        metadata["commonfields"]["id"] = skill_id
        metadata["id"] = skill_id  # parity with AgentixAgent helper
        metadata["name"] = name
        self.build(metadata=metadata, skill_content=skill_content)

    def update(self, update_obj: dict, key_dict_to_update: Optional[str] = None):
        """Update the ``<SkillName>.yml`` content, handling ``content`` specially.

        If ``content`` is present, write it to ``<SkillName>_skill.md`` instead of
        the YAML file (mirroring how the unifier merges them at upload time).
        """
        if "content" in update_obj:
            content = update_obj.pop("content")
            if content is not None:
                self.skill_content_file.write(content)

        if update_obj:
            super().update(update_obj, key_dict_to_update)
