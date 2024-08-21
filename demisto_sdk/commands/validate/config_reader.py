from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional

import toml

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.common.logger import logger

USE_GIT = "use_git"
PATH_BASED_VALIDATIONS = "path_based_validations"
DEFAULT_CATEGORY = "default_mandatory_validations"
PATH = Path(__file__).parents[0].resolve()
CONFIG_FILE_PATH = f"{PATH}/default_config.toml"


class ConfiguredValidations(NamedTuple):
    select: List[str] = []
    warning: List[str] = []
    ignorable_errors: List[str] = []
    support_level_dict: Dict[str, Dict[str, List[str]]] = {}


class ConfigReader:
    def __init__(
        self,
        path: Optional[Path] = None,
        category: Optional[str] = None,
        explicitly_selected: Optional[List[str]] = None,
    ):
        self.category_to_run = category
        self.explicitly_selected = explicitly_selected

        if path is None:
            path = Path(CONFIG_FILE_PATH)
        elif isinstance(path, str):
            path = Path(path)

        if not path.exists():
            logger.error(f"Config file {path} does not exist.")
            exit(1)

        self.config_file_content: dict = toml.load(path)

    def read(
        self,
        mode: Optional[ExecutionMode],
        ignore_support_level: Optional[bool] = False,
        codes_to_ignore: Optional[List[str]] = None,
    ) -> ConfiguredValidations:
        """Extract the relevant information from the relevant category in the config file.

        Args:
        Returns:
            Tuple[List, List, List, dict]: the select, warning, and ignorable errors sections from the given category,
            and the support_level dict with errors to ignore.
        """
        flag = self.category_to_run or (
            USE_GIT if mode == ExecutionMode.USE_GIT else PATH_BASED_VALIDATIONS
        )
        section = self.config_file_content.get(flag, {})
        explicitly_selected = sorted(filter(None, self.explicitly_selected or ()))

        select = explicitly_selected or sorted(section.get("select", []))
        warning = sorted(section.get("warning", []))
        ignorable = sorted(self.config_file_content.get("ignorable_errors", []))
        support_level_dict = (
            self.config_file_content.get("support_level", {})
            if not ignore_support_level
            else {}
        )

        def _ignore_errors(
            codes: Iterable[str], category: str, codes_to_ignore: Iterable[str]
        ) -> List[str]:
            """
            Removes the error codes we want to ignore, from a given list of error codes
            This is an internal method, since it's not supposed to be used elsewhere, and has a potentially-confusing name
            """
            codes = set(codes)
            if removed := codes.intersection(codes_to_ignore):
                logger.warning(
                    f"{category}: Removed ignored codes {','.join(sorted(removed))}"
                )
                return sorted(codes.difference(removed))
            else:
                logger.debug(f"{category}: nothing to filter out, using it as is")
                return sorted(codes)

        if codes_to_ignore:
            select = _ignore_errors(select, "select", codes_to_ignore)
            warning = _ignore_errors(warning, "warning", codes_to_ignore)
            explicitly_selected = _ignore_errors(
                explicitly_selected, "explicitly_selected", codes_to_ignore
            )

        return ConfiguredValidations(
            select=explicitly_selected or select,
            warning=warning,
            ignorable_errors=ignorable,
            support_level_dict=support_level_dict,
        )
