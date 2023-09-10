import itertools
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List

import typer
from git import Repo
from pydantic import ValidationError

# from demisto_sdk.__main__ import logging_setup_decorator, main
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.scripts.changelog.changelog_obj import (
    INITIAL_LOG,
    LogFileObject,
    LogLine,
    LogType,
)

CHANGELOG_FOLDER = Path(f"{git_path()}/.changelog")
CHANGELOG_MD_FILE = Path(f"{git_path()}/CHANGELOG.md")
RELEASE_VERSION_REGEX = re.compile(r"v\d{1,2}\.\d{1,2}\.\d{1,2}")

yaml = DEFAULT_YAML_HANDLER


class Changelog:
    def __init__(self, pr_number: str, pr_name: str = "") -> None:
        self.pr_number = pr_number
        self.pr_name = pr_name

    """ VALIDATE """

    def validate(self) -> None:
        """
        ...
        """
        if is_release(self.pr_name):
            _validate_release()
        else:
            _validate_branch(self.pr_number)

    """ INIT """

    def init(self) -> None:
        """
        Creates a new log file for the current PR with initial values,
        then the user has to change the values manually
        """
        if is_release(self.pr_name):
            raise RuntimeError(
                "This PR is a release (by its name), use the release command instead."
            )

        log = INITIAL_LOG
        log["pr_number"] = self.pr_number

        with (CHANGELOG_FOLDER / f"{self.pr_number}.yml").open("w") as f:
            yaml.dump(log, f)

        logger.info(f"Created changelog template at .changelog/{self.pr_number}.yml")

    """ RELEASE """

    def release(self) -> None:
        if not is_release(self.pr_name):
            raise ValueError("The PR name should match `v0.0.0` to start a release.")
        # get all log files as `LogFileObject`
        logs = get_all_logs()
        # get a dict sorted by type of log entry
        new_log_entries = get_new_log_entries(logs)
        new_changelog = compile_changelog_md(
            self.pr_name, new_log_entries, get_old_changelog()[1:]
        )
        write_to_changelog_file(new_changelog)
        logger.info("The changelog.md file has been successfully updated")
        clear_changelogs_folder()
        logger.info(f"Combined {len(logs)} changelog files into CHANGELOG.md")

    """ HELPER FUNCTIONS """


def is_changelog_modified() -> bool:
    return (
        "CHANGELOG.md"
        in Repo(".").git.diff("HEAD..origin/master", name_only=True).split()
    )


def is_log_folder_empty() -> bool:
    return not any(CHANGELOG_FOLDER.iterdir())


def is_log_yml_exist(pr_number: str) -> bool:
    return (CHANGELOG_FOLDER / f"{pr_number}.yml").exists()


def validate_log_yml(pr_number: str) -> None:
    data = get_yaml(CHANGELOG_FOLDER / f"{pr_number}.yml")

    try:
        LogFileObject(**data)
    except ValidationError as e:
        raise ValueError(e.json())


def get_all_logs() -> List[LogFileObject]:
    """
    Get all the log files under the .changelog folder,
    in case that one of the logs is not valid, an error is raised
    """
    changelogs: List[LogFileObject] = []
    errors: Dict[str, str] = {}
    for path in CHANGELOG_FOLDER.iterdir():
        try:
            changelogs.append(LogFileObject(**get_yaml(path)))
        except ValidationError as e:
            errors[f"{path}"] = e.json()

    if errors:
        for file_path, error in errors.items():
            logger.error(f"{file_path}:\n{error}\n")
        raise ValueError("One or more files were found invalid, see logs.")
    return changelogs


def get_new_log_entries(logs: List[LogFileObject]) -> Dict[str, List[LogLine]]:
    """
    Parses each LogFileObject and returns a dictionary classified by the type of log entry
    """
    all_logs_unreleased: List[LogLine] = []
    for log_file in logs:
        all_logs_unreleased.extend(log_file.get_log_entries())

    all_logs_unreleased_as_dict: Dict[str, List[LogLine]] = {}
    for type_, log_lines in itertools.groupby(all_logs_unreleased, lambda x: x.type):
        all_logs_unreleased_as_dict[type_] = list(log_lines)
    return all_logs_unreleased_as_dict


def get_old_changelog():
    return CHANGELOG_MD_FILE.read_text().splitlines()


def compile_changelog_md(
    pr_name: str, new_logs: Dict[str, List[LogLine]], old_changelog: List[str]
) -> str:
    """
    Builds the CHANGELOG.md content in stages
    """
    # The title
    new_changelog = ["# Changelog"]
    # New version (x.x.x)
    new_changelog.append(f"## {pr_name[1:]}")  # removes "v" prefix
    # Collecting the new log entries in the following order:
    # breaking, feature, fix, internal
    new_changelog.extend(
        [log_line.to_string() for log_line in new_logs.get(LogType.breaking, [])]
    )
    new_changelog.extend(
        [log_line.to_string() for log_line in new_logs.get(LogType.feature, [])]
    )
    new_changelog.extend(
        [log_line.to_string() for log_line in new_logs.get(LogType.fix, [])]
    )
    new_changelog.extend(
        [log_line.to_string() for log_line in new_logs.get(LogType.internal, [])]
    )
    # A new line separates versions
    new_changelog.append("\n")
    # Collecting the old changelog
    new_changelog.extend(old_changelog)
    return "\n".join(new_changelog)


def write_to_changelog_file(new_changelog: str) -> None:
    with CHANGELOG_MD_FILE.open("w") as f:
        f.write(new_changelog)


def clear_changelogs_folder() -> None:
    shutil.rmtree(CHANGELOG_FOLDER)
    CHANGELOG_FOLDER.mkdir()
    logger.info("Cleanup of `.changelog` folder completed successfully")


def is_release(pr_name: str) -> bool:
    return pr_name is not None and RELEASE_VERSION_REGEX.match(pr_name) is not None


def _validate_release() -> None:
    if not is_log_folder_empty():
        raise ValueError(
            "Logs folder is not empty,\n"
            "It is not possible to release until the `changelog.md` "
            "file is updated, and the `.changelog` folder is empty"
        )
    if not is_changelog_modified():
        raise ValueError(
            "The file `changelog.md` is not updated\n"
            "It is not possible to release until the `changelog.md` "
            "file is updated, and the `.changelog` folder is empty"
        )


def _validate_branch(pr_number: str) -> None:
    if is_changelog_modified():
        raise ValueError(
            "Do not modify changelog.md\n"
            "run `demisto-sdk changelog --init -pn <pr number> -pt <pr name>`"
            " to create a log file instead."
        )
    if not is_log_yml_exist(pr_number):
        raise ValueError(
            "Missing changelog file.\n"
            "Run `demisto-sdk changelog --init -pn <pr number> -pt <pr name>` and fill it."
        )
    validate_log_yml(pr_number)


main = typer.Typer()

release = typer.Option(False, "--release", help="releasing", is_flag=True)
init = typer.Option(
    False, "--init", help="Generates a log file for the current PR", is_flag=True
)
validate = typer.Option(
    False,
    "--validate",
    help="Checks whether there is a log file for the current PR, if so checks whether the log file is valid",
    is_flag=True,
)

pr_number = typer.Option(..., "--pr_number", "-n", help="Pull request number")

pr_title = typer.Option("", "--pr_title", "-t", help="Pull request title (used for release)")


@main.command()
def changelog_management(
    init: bool = init,
    validate: bool = validate,
    release: bool = release,
    pr_number: str = pr_number,
    pr_name: str = pr_title,
):
    pr_name = pr_name
    pr_number = pr_number

    if not pr_number:
        raise ValueError("No provided the `pr_number` argument")
    changelog = Changelog(pr_number, pr_name)
    if validate:
        return changelog.validate()
    elif init:
        return changelog.init()
    elif release:
        return changelog.release()
    else:
        raise ValueError(
            "Missing arguments, run `demisto-sdk changelog --help` to see which arguments are required"
        )


if __name__ == "__main__":
    main()
