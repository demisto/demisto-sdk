import copy
from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.files import TextFile
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.prepare_content.unifier import Unifier


class AgentixAgentUnifier(Unifier):
    """
    Unifier for AgentixAgent content items.

    This class handles merging system instructions from a separate file into the
    agent's YAML during the content creation process.

    The system instructions file follows the naming convention:
    `<agent_folder_name>_systeminstructions.md`

    Directory structure:
    AgentixAgents/AgentName/
    ├── AgentName.yml
    └── AgentName_systeminstructions.md
    """

    # File suffix for system instructions
    SYSTEM_INSTRUCTIONS_SUFFIX = "_systeminstructions.md"

    @staticmethod
    def unify(
        path: Path,
        data: dict,
        marketplace: Optional[MarketplaceVersions] = None,
        **kwargs,
    ) -> dict:
        """
        Merges system instructions from a separate file into the YAML.

        Args:
            path: Path to the agent YAML file
            data: Parsed YAML data
            marketplace: Target marketplace (unused for agents, kept for interface compatibility)
            **kwargs: Additional arguments (unused)

        Returns:
            Unified YAML dict with systeminstructions field populated from file
        """
        logger.debug(f"Unifying AgentixAgent: {path}")

        package_path = path.parent
        yml_unified = copy.deepcopy(data)

        # Find and insert system instructions
        yml_unified = AgentixAgentUnifier.insert_system_instructions_to_yml(
            package_path, yml_unified
        )

        logger.debug(f"<green>Created unified AgentixAgent yml: {path.name}</green>")
        return yml_unified

    @staticmethod
    def get_system_instructions_file(package_path: Path) -> Optional[Path]:
        """
        Find the system instructions file in the package directory.

        The file should be named: <agent_folder_name>_systeminstructions.md

        Args:
            package_path: Path to the agent package directory

        Returns:
            Path to the system instructions file if found, None otherwise
        """
        # Get the folder name (which should match the agent name pattern)
        folder_name = package_path.name

        # Build the expected system instructions file path
        instructions_file = (
            package_path / f"{folder_name}{AgentixAgentUnifier.SYSTEM_INSTRUCTIONS_SUFFIX}"
        )

        if instructions_file.exists():
            return instructions_file

        return None

    @staticmethod
    def insert_system_instructions_to_yml(
        package_path: Path, yml_unified: dict
    ) -> dict:
        """
        Read system instructions from file and add to YAML.

        Args:
            package_path: Path to the agent package directory
            yml_unified: The YAML dict to update

        Returns:
            Updated YAML dict with systeminstructions field
        """
        instructions_file = AgentixAgentUnifier.get_system_instructions_file(package_path)

        if instructions_file:
            try:
                instructions_content = instructions_file.read_text(encoding="utf-8")
                yml_unified["systeminstructions"] = instructions_content.strip()
                logger.debug(
                    f"Inserted system instructions from '{instructions_file.name}'"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to read system instructions file '{instructions_file}': {e}"
                )
        else:
            logger.debug(
                f"No system instructions file found in '{package_path}'"
            )

        return yml_unified

    @staticmethod
    def get_system_instructions(package_path: Path) -> str:
        """
        Get system instructions content from the package directory.

        This method is used by the parser to read system instructions from the
        separate file during content graph parsing.

        Args:
            package_path: Path to the agent package directory

        Returns:
            The system instructions content, or empty string if not found
        """
        instructions_file = AgentixAgentUnifier.get_system_instructions_file(package_path)

        if instructions_file:
            try:
                return instructions_file.read_text(encoding="utf-8").strip()
            except Exception as e:
                logger.warning(
                    f"Failed to read system instructions file '{instructions_file}': {e}"
                )
        return ""

    @staticmethod
    def get_system_instructions_with_sha(yml_path: Path, git_sha: str) -> str:
        """
        Get system instructions content from a specific git commit.

        This method is used when comparing content between different versions
        (e.g., for backward compatibility checks).

        Args:
            yml_path: Path to the agent YAML file
            git_sha: The git commit SHA to read from

        Returns:
            The system instructions content, or empty string if not found
        """
        # Build the expected system instructions file path
        folder_name = yml_path.parent.name
        instructions_file_path = str(
            yml_path.parent / f"{folder_name}{AgentixAgentUnifier.SYSTEM_INSTRUCTIONS_SUFFIX}"
        )

        try:
            content = TextFile.read_from_git_path(instructions_file_path, tag=git_sha)
            return content.strip() if content else ""
        except Exception as e:
            logger.debug(
                f"Could not read system instructions from git sha {git_sha}: {e}"
            )
            return ""