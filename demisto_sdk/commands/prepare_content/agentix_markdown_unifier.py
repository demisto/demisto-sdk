import copy
import re
from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.files import TextFile
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.prepare_content.unifier import Unifier

# AgentixSkill: skill body lives in "<folder>_skill.md" and is unified into "content".
AGENTIX_SKILL_TARGET_FIELD = "content"
AGENTIX_SKILL_FILE_SUFFIX = "_skill.md"

# Matches ``<action=action-id>`` tokens in a skill's Markdown body.
ACTION_REFERENCE_REGEX = re.compile(r"<action=([^>]+)>")

# AgentixAgent: system instructions live in "<folder>_systeminstructions.md"
# and are unified into "systeminstructions".
AGENTIX_AGENT_TARGET_FIELD = "systeminstructions"
AGENTIX_AGENT_FILE_SUFFIX = "_systeminstructions.md"


class AgentixMarkdownUnifier(Unifier):
    """
    Generic unifier for Agentix content items that store part of their content
    in a separate Markdown file alongside the main file.

    During unification, the Markdown file's text is read and inserted into a
    single target field of the content item's data dict.

    Callers configure two things per content type:
    - ``target_field``: the key in the data dict to populate with the file text
      (e.g. ``content`` for skills, ``systeminstructions`` for agents).
    - The Markdown file name, supplied either as:
        * ``file_name`` - a fixed file name, or
        * ``file_suffix`` - a suffix appended to the package folder name
          (e.g. ``_skill.md`` -> ``<folder>_skill.md``, or
          ``_systeminstructions.md`` -> ``<folder>_systeminstructions.md``).

    Exactly one of ``file_name`` / ``file_suffix`` must be provided.
    """

    @staticmethod
    def _resolve_markdown_file_path(
        package_path: Path,
        *,
        file_name: Optional[str] = None,
        file_suffix: Optional[str] = None,
    ) -> Path:
        """
        Build the expected Markdown file path for the given package directory.

        Args:
            package_path: Path to the content item package directory
            file_name: Fixed Markdown file name
            file_suffix: Suffix appended to the package folder name

        Returns:
            The expected path to the Markdown file (may or may not exist)
        """
        if file_name and file_suffix:
            raise ValueError("Provide only one of 'file_name' or 'file_suffix'.")
        if file_name:
            return package_path / file_name
        if file_suffix:
            return package_path / f"{package_path.name}{file_suffix}"
        raise ValueError("One of 'file_name' or 'file_suffix' must be provided.")

    @classmethod
    def _get_existing_markdown_file(
        cls,
        package_path: Path,
        *,
        file_name: Optional[str] = None,
        file_suffix: Optional[str] = None,
    ) -> Optional[Path]:
        """Return the Markdown file path if it exists, otherwise None."""
        markdown_file = cls._resolve_markdown_file_path(
            package_path, file_name=file_name, file_suffix=file_suffix
        )
        return markdown_file if markdown_file.exists() else None

    @classmethod
    def unify(
        cls,
        path: Path,
        data: dict,
        marketplace: Optional[MarketplaceVersions] = None,
        *,
        target_field: Optional[str] = None,
        file_name: Optional[str] = None,
        file_suffix: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """
        Merge the Markdown file content into the data dict.

        Args:
            path: Path to the content item's main file (yml/metadata)
            data: Parsed data of the content item
            marketplace: Target marketplace (unused, kept for interface compatibility)
            target_field: The key in the data dict to populate (required)
            file_name: Fixed Markdown file name (mutually exclusive with file_suffix)
            file_suffix: Suffix appended to the package folder name
            **kwargs: Additional arguments (unused)

        Returns:
            Unified dict with ``target_field`` populated from the Markdown file
        """
        if not target_field:
            raise ValueError("'target_field' must be provided.")

        logger.debug(f"Unifying Agentix Markdown file: {path}")

        package_path = path.parent
        unified = copy.deepcopy(data)
        markdown_file = cls._get_existing_markdown_file(
            package_path, file_name=file_name, file_suffix=file_suffix
        )

        if markdown_file:
            try:
                content = markdown_file.read_text(encoding="utf-8")
                unified[target_field] = content.strip()
                logger.debug(f"Inserted content from '{markdown_file.name}'")
            except Exception as e:
                logger.warning(f"Failed to read Markdown file '{markdown_file}': {e}")
        else:
            logger.debug(f"No Markdown file found in '{package_path}'")

        # Rename 'collectionids' (source field) to 'systemknowledgecollectionids' (server field)
        if target_field == AGENTIX_AGENT_TARGET_FIELD and "collectionids" in unified:
            unified["systemknowledgecollectionids"] = unified.pop("collectionids")

        logger.debug(f"<green>Created unified Agentix item: {path.name}</green>")
        return unified

    @classmethod
    def get_content(
        cls,
        package_path: Path,
        *,
        file_name: Optional[str] = None,
        file_suffix: Optional[str] = None,
    ) -> str:
        """
        Read the Markdown file content from the package directory.

        Used by parsers during content graph parsing.

        Args:
            package_path: Path to the content item package directory
            file_name: Fixed Markdown file name (mutually exclusive with file_suffix)
            file_suffix: Suffix appended to the package folder name

        Returns:
            The Markdown file content, or empty string if not found
        """
        markdown_file = cls._get_existing_markdown_file(
            package_path, file_name=file_name, file_suffix=file_suffix
        )

        if markdown_file:
            try:
                return markdown_file.read_text(encoding="utf-8").strip()
            except Exception as e:
                logger.warning(f"Failed to read Markdown file '{markdown_file}': {e}")
        return ""

    @classmethod
    def get_content_with_sha(
        cls,
        main_file_path: Path,
        git_sha: str,
        *,
        file_name: Optional[str] = None,
        file_suffix: Optional[str] = None,
    ) -> str:
        """
        Read the Markdown file content from a specific git commit.

        Used when comparing content between versions (e.g. backward
        compatibility checks).

        Args:
            main_file_path: Path to the content item's main file (yml/metadata)
            git_sha: The git commit SHA to read from
            file_name: Fixed Markdown file name (mutually exclusive with file_suffix)
            file_suffix: Suffix appended to the package folder name

        Returns:
            The Markdown file content, or empty string if not found
        """
        markdown_file_path = str(
            cls._resolve_markdown_file_path(
                main_file_path.parent, file_name=file_name, file_suffix=file_suffix
            )
        )

        try:
            content = TextFile.read_from_git_path(markdown_file_path, tag=git_sha)
            return content.strip() if content else ""
        except Exception as e:
            logger.debug(f"Could not read Markdown file from git sha {git_sha}: {e}")
            return ""
