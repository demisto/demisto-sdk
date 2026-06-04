import copy
from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.files import TextFile
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.prepare_content.unifier import Unifier


class AgentixSkillUnifier(Unifier):
    """
    Unifier for AgentixSkill content items.

    This class handles merging the skill body (Markdown) from a separate file
    into the skill's ``metadata.yml`` during the content creation process.

    The skill body file follows the naming convention:
    ``skill.md``

    Directory structure:
    AgentixSkills/SkillName/
    ├── metadata.yml
    └── skill.md
    """

    # File name for the skill body
    SKILL_CONTENT_FILE_NAME = "skill.md"

    @staticmethod
    def unify(
        path: Path,
        data: dict,
        marketplace: Optional[MarketplaceVersions] = None,
        **kwargs,
    ) -> dict:
        """
        Merges skill body from a separate file into the metadata dict.

        Args:
            path: Path to the skill ``metadata.yml`` file
            data: Parsed metadata YAML data
            marketplace: Target marketplace (unused for skills, kept for interface compatibility)
            **kwargs: Additional arguments (unused)

        Returns:
            Unified dict with ``content`` field populated from the skill.md file
        """
        logger.debug(f"Unifying AgentixSkill: {path}")

        package_path = path.parent
        unified = copy.deepcopy(data)

        # Find and insert skill body content
        unified = AgentixSkillUnifier.insert_skill_content_to_metadata(
            package_path, unified
        )

        logger.debug(f"<green>Created unified AgentixSkill metadata: {path.name}</green>")
        return unified

    @staticmethod
    def get_skill_content_file(package_path: Path) -> Optional[Path]:
        """
        Find the skill body (Markdown) file in the package directory.

        The file should be named: ``skill.md``

        Args:
            package_path: Path to the skill package directory

        Returns:
            Path to the skill body file if found, None otherwise
        """
        content_file = package_path / AgentixSkillUnifier.SKILL_CONTENT_FILE_NAME

        if content_file.exists():
            return content_file

        return None

    @staticmethod
    def insert_skill_content_to_metadata(
        package_path: Path, unified: dict
    ) -> dict:
        """
        Read skill body from file and add to the unified metadata dict.

        Args:
            package_path: Path to the skill package directory
            unified: The metadata dict to update

        Returns:
            Updated metadata dict with the ``content`` field populated
        """
        content_file = AgentixSkillUnifier.get_skill_content_file(package_path)

        if content_file:
            try:
                skill_content = content_file.read_text(encoding="utf-8")
                unified["content"] = skill_content.strip()
                logger.debug(f"Inserted skill content from '{content_file.name}'")
            except Exception as e:
                logger.warning(
                    f"Failed to read skill content file '{content_file}': {e}"
                )
        else:
            logger.debug(f"No skill content file found in '{package_path}'")

        return unified

    @staticmethod
    def get_skill_content(package_path: Path) -> str:
        """
        Get the skill body content from the package directory.

        This method is used by the parser to read the skill body from the
        separate file during content graph parsing.

        Args:
            package_path: Path to the skill package directory

        Returns:
            The skill body content, or empty string if not found
        """
        content_file = AgentixSkillUnifier.get_skill_content_file(package_path)

        if content_file:
            try:
                return content_file.read_text(encoding="utf-8").strip()
            except Exception as e:
                logger.warning(
                    f"Failed to read skill content file '{content_file}': {e}"
                )
        return ""

    @staticmethod
    def get_skill_content_with_sha(metadata_path: Path, git_sha: str) -> str:
        """
        Get the skill body content from a specific git commit.

        This method is used when comparing content between different versions
        (e.g., for backward compatibility checks).

        Args:
            metadata_path: Path to the skill ``metadata.yml`` file
            git_sha: The git commit SHA to read from

        Returns:
            The skill body content, or empty string if not found
        """
        content_file_path = str(
            metadata_path.parent / AgentixSkillUnifier.SKILL_CONTENT_FILE_NAME
        )

        try:
            content = TextFile.read_from_git_path(content_file_path, tag=git_sha)
            return content.strip() if content else ""
        except Exception as e:
            logger.debug(
                f"Could not read skill content from git sha {git_sha}: {e}"
            )
            return ""
