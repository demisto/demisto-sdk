import re
import shutil
from pathlib import Path
from typing import List

from git import Repo
from pydantic import ValidationError

from demisto_sdk.commands.changelog.changelog_obj import INITIAL_LOG, LogObject
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_yaml

CHANGELOG_FOLDER = Path(f"{git_path()}/.changelog")
CHANGELOG_MD_FILE = Path(f"{git_path()}/CHANGELOG.md")
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
            if not self.is_log_folder_empty():
                logger.error("Something msg")
                return False
            if not self.is_changelog_changed():
                logger.error("Something msg")
                return False
        else:
            if self.is_changelog_changed():
                logger.error("Something msg")
                return False
            if not self.is_log_yml_exist():
                logger.error("Something msg")
                return False
            if not self.validate_log_yml():
                logger.error("Something msg")
                return False

        return True

    """ INIT """

    def init(self) -> None:
        """
        Creates a new log file for the current PR
        """
        if self.is_release():
            logger.error(
                "This PR is for release, please use in changelog release command"
            )

        with Path(f"{git_path()}/.changelog/{self.pr_number}.yml").open("w") as f:
            yaml.dump(INITIAL_LOG, f)

        logger.info("Something msg")

    """ RELEASE """

    def release(self) -> None:
        if not self.is_release():
            logger.error("Something msg")
            return
        logs = self.get_all_logs()
        self.extract_and_build_changelogs(logs)
        self.cleaning_changelogs_folder()
        logger.info("end")

    """ HELPER FUNCTIONS """

    def is_changelog_changed(self) -> bool:
        return "CHANGELOG.md" in Repo(".").git.diff('HEAD..master', name_only=True).split()

    def is_log_folder_empty(self) -> bool:
        return not any(CHANGELOG_FOLDER.iterdir())

    def is_log_yml_exist(self) -> bool:
        return Path(f"{git_path()}/.changelog/{self.pr_number}.yml").is_file()

    def validate_log_yml(self) -> bool:
        data = get_yaml(Path(f"{git_path()}/.changelog/{self.pr_number}.yml"))
        
        try:
            LogObject(**data)
        except ValidationError as e:
            logger.error(e.json())
            return False
        return True

    def get_all_logs(self) -> List[LogObject]:
        changelogs: List[LogObject] = []
        for path in CHANGELOG_FOLDER.iterdir():
            changelog_data = get_yaml(path)
            try:
                changelogs.append(LogObject(**changelog_data))
            except ValidationError as e:
                logger.error(f"{path}: {e.json()}")

        return changelogs

    def extract_and_build_changelogs(self, logs: List[LogObject]) -> None:
        all_logs_unreleased: List[str] = []
        for log in logs:
            all_logs_unreleased.extend(log.build_log())
        with CHANGELOG_MD_FILE.open() as f:
            old_changelog = f.readlines()

        new_changelog = self.prepare_new_changelog(all_logs_unreleased, old_changelog[1:])
        self.write_to_changelog_file(new_changelog)
        logger.info("")

    def prepare_new_changelog(self, new_logs: List[str], old_changelog: List[str]) -> str:
        new_changelog = "# Changelog\n"
        new_changelog += f"## {self.pr_name[1:]}\n"
        for log in new_logs:
            new_changelog += log
        new_changelog += "\n"
        for log in old_changelog:
            new_changelog += log
        return new_changelog

    def write_to_changelog_file(self, new_changelog: str) -> None:
        with CHANGELOG_MD_FILE.open('w') as f:
            f.write(new_changelog)

    def cleaning_changelogs_folder(self) -> None:
        for item in CHANGELOG_FOLDER.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        logger.info("Something msg")


Changelog("12345", "v2.0.0").release()