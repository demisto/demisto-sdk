import re
import shutil
import sys
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
        self, pr_number: str, pr_name: str = '', release_version: str = None
    ) -> None:
        self.pr_number = pr_number
        self.pr_name = pr_name
        self.handle_error = ""


    """ VALIDATE """

    def validate(self) -> bool:
        """
        ...
        """
        if self.is_release():
            if not self.is_log_folder_empty():
                logger.error("Logs folder is not empty,\n"
                             "It is not possible to release until the `changelog.md` "
                             "file is updated, and the `.changelog` folder is empty")
                return False
            if not self.is_changelog_changed():
                logger.error("The file `changelog.md` is not updated\n"
                             "It is not possible to release until the `changelog.md` "
                             "file is updated, and the `.changelog` folder is empty")
                return False
        else:
            if self.is_changelog_changed():
                logger.error("It is not possible to make a change in the `changelog.md` file,\n"
                             "run `demisto-sdk changelog --init -pn <pr number> -pt <pr name>` to create log file,\n"
                             "and put the description of your changes there")
                return False
            if not self.is_log_yml_exist():
                logger.error("There is no log file describing your change,\n"
                             "Please run `demisto-sdk changelog --init -pn <pr number> -pt <pr name>` to create one, "
                             "and put the description of your changes there")
                return False
            if not self.validate_log_yml():
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

        with (CHANGELOG_FOLDER / f"{self.pr_number}.yml").open("w") as f:
            yaml.dump(INITIAL_LOG, f)

        logger.info(f"The creation of the log file .changelog/{self.pr_number}.yml is complete,\n"
                     "Please go to the file and edit the initial values.")

    """ RELEASE """

    def release(self) -> None:
        if not self.is_release():
            logger.error("The name of the PR is not valid for a release")
            raise ValueError()
        logs = self.get_all_logs()
        self.extract_and_build_changelogs(logs)
        self.cleaning_changelogs_folder()
        logger.info("The build of the changelog for the release is complete")

    """ HELPER FUNCTIONS """

    def is_changelog_changed(self) -> bool:
        return "CHANGELOG.md" in Repo(".").git.diff('HEAD..master', name_only=True).split()

    def is_log_folder_empty(self) -> bool:
        return not any(CHANGELOG_FOLDER.iterdir())

    def is_log_yml_exist(self) -> bool:
        return (CHANGELOG_FOLDER / f"{self.pr_number}.yml").is_file()

    def validate_log_yml(self) -> bool:
        data = get_yaml(CHANGELOG_FOLDER / f"{self.pr_number}.yml")
        
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
                self.handle_error += f"{path}: {e.json()}\n"

        if self.handle_error:
            raise ValueError(f"The following log files are invalid:ֿֿ\n{self.handle_error}")
        return changelogs

    def extract_and_build_changelogs(self, logs: List[LogObject]) -> None:
        all_logs_unreleased: List[str] = []
        breaking_logs: List[str] = []
        feature_logs: List[str] = []
        fix_logs: List[str] = []
        for log in logs:
            breaking_log, feature_log, fix_log = log.build_log()
            breaking_logs.extend(breaking_log)
            feature_logs.extend(feature_log)
            fix_logs.extend(fix_log)
        for type_log in (breaking_logs, feature_logs, fix_logs):
            all_logs_unreleased.extend(type_log)
        with CHANGELOG_MD_FILE.open() as f:
            old_changelog = f.readlines()

        new_changelog = self.prepare_new_changelog(all_logs_unreleased, old_changelog[1:])
        self.write_to_changelog_file(new_changelog)
        logger.info("The changelog.md file has been successfully updated")

    def prepare_new_changelog(self, new_logs: List[str], old_changelog: List[str]) -> str:
        # self.get_current_version(old_changelog)
        new_changelog = "# Changelog\n"
        new_changelog += f"## {self.pr_name[1:]}\n"
        for log in new_logs:
            new_changelog += log
        new_changelog += "\n"
        for log in old_changelog:
            new_changelog += log
        return new_changelog

    def get_current_version(self, old_changelog: List[str]) -> str:
        for line in old_changelog:
            if RELEASE_VERSION_REGEX.match(line) is not None:
                return line
        raise ValueError("Could not find the current version")

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

    def is_release(self) -> bool:
        return (
            RELEASE_VERSION_REGEX.match(self.pr_name) is not None
            if self.pr_name
            else False
        )


def changelog_management(**kwargs):
    pr_name = kwargs.get("pr_title", '')
    pr_number = kwargs.get("pr_number", None)
    validate = kwargs.get("validate", None)
    init = kwargs.get("init", None)
    release = kwargs.get("release", None)
    
    if not pr_number:
        logger.error("No provided the pr_number argument")
        sys.exit(1)

    changelog = Changelog(pr_number, pr_name)
    if validate:
        return changelog.validate()
    elif init:
        return changelog.init()
    elif release:
        return changelog.release()
    else:
        logger.error("")
        return 1
