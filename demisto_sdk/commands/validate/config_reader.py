from typing import List, Tuple

import toml

from demisto_sdk.commands.common.constants import DEFAULT_MANDATORY_VALIDATIONS

CONFIG_FILE_PATH = (
    "/Users/yhayun/dev/demisto/demisto-sdk/demisto_sdk/commands/validate/config.toml"
)
USE_GIT = "use_git"
VALIDATE_ALL = "validate_all"


class ConfigReader:
    def __init__(self, config_file_path, category_to_run):
        if not config_file_path:
            config_file_path = CONFIG_FILE_PATH
        self.config_file_path = config_file_path
        try:
            self.config_file_content: dict = toml.load(self.config_file_path)
            self.category_to_run = category_to_run
        except FileNotFoundError:
            self.config_file_content = DEFAULT_MANDATORY_VALIDATIONS
            self.category_to_run = "default_mandatory_validations"

    def gather_validations_to_run(self, use_git: bool) -> Tuple[List, List, List, dict]:
        """Extract the relevant information from the relevant category in the config file.

        Args:
            use_git (bool): The use_git flag.

        Returns:
            Tuple[List, List, List, dict]: the select, warning, and ignorable errors sections from the given category,
            and the support_level dict with errors to ignore.
        """
        flag = self.category_to_run or USE_GIT if use_git else VALIDATE_ALL
        section = self.config_file_content.get(flag, {})
        return (
            section.get("select"),
            section.get("warning"),
            section.get("ignorable_errors"),
            self.config_file_content.get("support_level", {}),
        )
