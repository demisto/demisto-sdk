from pathlib import Path
from typing import Dict, List, Optional

import toml

from demisto_sdk.commands.common.logger import logger

USE_GIT = "use_git"
VALIDATE_ALL = "validate_all"
DEFAULT_CATEGORY = "default_mandatory_validations"
PATH = Path(__file__).parents[0].resolve()
CONFIG_FILE_PATH = f"{PATH}/default_config.toml"


class ConfiguredValidations:
    """
    class to hold all the sections from the config file as one object
    """

    def __init__(
        self,
        select: List[str] = [],
        warning: List[str] = [],
        ignorable_errors: List[str] = [],
        support_level_dict: Dict[str, str] = {},
    ):
        self.validations_to_run = select
        self.only_throw_warnings = warning
        self.ignorable_errors = ignorable_errors
        self.support_level_dict = support_level_dict


class ConfigReader:
    def __init__(self, config_file_path=None, category_to_run=None):
        if not config_file_path:
            config_file_path = CONFIG_FILE_PATH
        try:
            self.config_file_content: dict = toml.load(config_file_path)
            self.category_to_run = category_to_run
        except FileNotFoundError:
            logger.error(f"Failed to find config file at path {config_file_path}")
            exit(1)

    def gather_validations_to_run(
        self, use_git: bool, ignore_support_level: Optional[bool] = False
    ) -> ConfiguredValidations:
        """Extract the relevant information from the relevant category in the config file.

        Args:
            use_git (bool): The use_git flag.

        Returns:
            Tuple[List, List, List, dict]: the select, warning, and ignorable errors sections from the given category,
            and the support_level dict with errors to ignore.
        """
        flag = self.category_to_run or (USE_GIT if use_git else VALIDATE_ALL)
        section = self.config_file_content.get(flag, {})
        return ConfiguredValidations(
            section.get("select", []),
            section.get("warning", []),
            self.config_file_content.get("ignorable_errors", []),
            self.config_file_content.get("support_level", {})
            if not ignore_support_level
            else {},
        )
