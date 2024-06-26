from collections.abc import Iterable
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

import toml

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
    support_level_dict: Dict[str, str] = {}


class ConfigReader:
    def __init__(
        self,
        path: Optional[Path] = None,
        category: Optional[str] = None,
    ):
        if path is None:
            path = Path(CONFIG_FILE_PATH)

        if not path.exists():
            logger.error(f"Config file {path} does not exist.")
            exit(1)

        self.config_file_content: dict = toml.load(path)
        self.category_to_run = category

    def read(
        self,
        use_git: bool,
        ignore_support_level: Optional[bool] = False,
        codes_to_ignore: Optional[List[str]] = None,
    ) -> ConfiguredValidations:
        """Extract the relevant information from the relevant category in the config file."""
        flag = self.category_to_run or (USE_GIT if use_git else PATH_BASED_VALIDATIONS)
        section = self.config_file_content.get(flag, {})

        select = sorted(section.get("select", []))
        warning = sorted(section.get("warning", []))
        ignorable = sorted(self.config_file_content.get("ignorable_errors", []))
        support_level_dict = (
            self.config_file_content.get("support_level", {})
            if not ignore_support_level
            else {}
        )

        if codes_to_ignore:
            check_ignored_are_ignorable(codes_to_ignore, ignorable)
            select = remove_ignored(select, "select", codes_to_ignore)
            warning = remove_ignored(warning, "warning", codes_to_ignore)

        return ConfiguredValidations(
            select=select,
            warning=warning,
            ignorable_errors=ignorable,
            support_level_dict=support_level_dict,
        )


def check_ignored_are_ignorable(
    codes_to_ignore: Optional[List[str]], ignorable: List[str]
):
    if not codes_to_ignore:
        return

    if cannot_be_ignored := set(codes_to_ignore).difference(ignorable):
        logger.error(
            f"{','.join(sorted(cannot_be_ignored))} are not under `ignorable_errors` in the config file, cannot be ignored."
        )
        exit(1)


def remove_ignored(
    codes: Iterable[str], category: str, codes_to_ignore: Iterable[str]
) -> List[str]:
    codes = set(codes)
    if removed := codes.intersection(codes_to_ignore):
        logger.warning(f"{category}: Removed ignored codes {','.join(sorted(removed))}")
        return sorted(codes.difference(removed))
    else:
        logger.debug(f"{category}: nothing to filter out, using it as is")
        return sorted(codes)
