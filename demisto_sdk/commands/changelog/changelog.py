import re
import shutil
from pathlib import Path
from typing import List

from pydantic import ValidationError

from demisto_sdk.commands.changelog.changelog_obj import ChangelogObject, ChangelogType
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_yaml

CHANGELOG_FOLDER = Path(f"{git_path()}/.changelog")
RELEASE_VERSION_REGEX = re.compile(r"v\d{1,2}\.\d{1,2}\.\d{1,2}")

yaml = YAML_Handler()


class Changelog:
    def __init__(
        self, pr_number: str, pr_name: str = None, release_version: str = None
    ) -> None:
        self.pr_number = pr_number
        self.pr_name = pr_name
        self.release_version = release_version

    def is_release(self) -> bool:
        return (
            RELEASE_VERSION_REGEX.match(self.pr_name) is not None
            if self.pr_name
            else False
        )

    """ VALIDATE """

    def validate(self) -> bool:
        """
        ...
        """
        if self.is_release():
            if not self.is_changelog_folder_empty():
                logger.error("Something msg")
                return False
            if not self.is_changelog_changed():
                logger.error("Something msg")
                return False
        else:
            if self.is_changelog_changed():
                logger.error("Something msg")
                return False
            if not self.is_changelog_yml_exist():
                logger.error("Something msg")
                return False
            if not self.validate_changelog_yml():
                logger.error("Something msg")
                return False
        return True

    """ INIT """

    def init(self) -> None:
        """
        Creates a new changelog file for the current PR
        """
        if self.is_release():
            logger.error(
                "This PR is for release, please use in changelog release command"
            )
        initial_changelog = {
            "description": "enter description about this PR",
            "type": "<fix|feature|breaking>",
        }
        try:
            new_obj = ChangelogObject(**initial_changelog)
        except ValidationError as e:
            logger.error(e.json())

        with Path(f"{git_path()}/.changelog/{self.pr_number}.yml").open("w") as f:
            yaml.dump(new_obj.dict(), f)

        logger.info("Something msg")

    """ RELEASE """

    def release(self) -> None:
        if not self.is_release():
            logger.error("Something msg")
            return
        changelogs = self.get_all_changelogs()
        self.edit_changelog_file(changelogs)
        self.cleaning_changelogs_folder()

    """ HELPER FUNCTIONS """

    def is_changelog_changed(self) -> bool:
        ...

    def is_changelog_folder_empty(self) -> bool:
        return any(CHANGELOG_FOLDER.iterdir())

    def is_changelog_yml_exist(self) -> bool:
        return Path(f"{git_path()}/{self.pr_number}.yml").is_file()

    def validate_changelog_yml(self) -> bool:
        data = get_yaml(Path(f"{git_path()}/.changelog/{self.pr_number}.yml"))
        try:
            ChangelogObject(**data)
        except ValidationError as e:
            logger.error(e.json())
            return False
        return True

    def get_all_changelogs(self) -> List[ChangelogObject]:
        changelogs: List[ChangelogObject] = []
        for path in CHANGELOG_FOLDER.iterdir():
            changelog_data = get_yaml(path)
            try:
                changelogs.append(ChangelogObject(**changelog_data))
            except ValidationError as e:
                logger.error(f"{path}: {e.json()}")

        return changelogs

    def edit_changelog_file(self, changelogs: List[ChangelogObject]) -> None:
        fixes = tuple(
            filter(
                lambda f: f.description if f.type == ChangelogType.fix else None,
                changelogs,
            )
        )
        features = tuple(
            filter(
                lambda f: f.description if f.type == ChangelogType.feature else None,
                changelogs,
            )
        )
        breakings = tuple(
            filter(
                lambda f: f.description if f.type == ChangelogType.breaking else None,
                changelogs,
            )
        )

    def cleaning_changelogs_folder(self) -> None:
        for item in CHANGELOG_FOLDER.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        logger.info("Something msg")
