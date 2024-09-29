import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import typer
from git import Repo  # noqa: TID251
from github import Github
from more_itertools import bucket
from pydantic import ValidationError

from demisto_sdk.commands.common.files.yml_file import YmlFile
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import (
    DEFAULT_JSON_HANDLER,
    DEFAULT_YAML_HANDLER,
)
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.logger import logger, logging_setup
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.scripts.changelog.changelog_obj import (
    INITIAL_LOG,
    LogFileObject,
    LogLine,
    LogType,
)

logging_setup(calling_function=Path(__file__).stem)

DEMISTO_SDK_REPO = "demisto/demisto-sdk"
CHANGELOG_FOLDER = Path(f"{git_path()}/.changelog")
CHANGELOG_MD_FILE = Path(f"{git_path()}/CHANGELOG.md")
RELEASE_VERSION_REGEX = re.compile(r"demisto-sdk release \d{1,2}\.\d{1,2}\.\d{1,2}")
GIT_UTIL = GitUtil(".")
yaml = DEFAULT_YAML_HANDLER
json = DEFAULT_JSON_HANDLER
sys.tracebacklimit = 0


class Changelog:
    def __init__(self, pr_number: str, pr_name: str = "") -> None:
        self.pr_number = pr_number
        self.pr_name = pr_name

    """ VALIDATE """

    def validate(self) -> None:
        """
        Checks the following:
            - If the PR is a release:
                - checks that the `.changelog` folder is empty ????
                - checks that the `CHANGELOG.md` file has changed ????
            - If the PR is normal:
                - checks that the `CHANGELOG.md` file has not changed
                - checks that a log file has been added and its name is the same as the PR name
                - ensure that the added log file is valid according to the `LogFileObject` model convention

        Prints out a comment on how the PR would look like with the rn

        """
        if is_release(self.pr_name):
            return
        else:
            _validate_branch(self.pr_number)

    """ Comment """

    def comment(self, latest_commit: str, github_token: str) -> None:
        """
        Comment on the PR

        Checks the following:
            - If the changelog file has been added in latest commit OR If the changelog file has been
                modified between the last two commits.

        """
        changelog_path = CHANGELOG_FOLDER / f"{self.pr_number}.yml"

        previous_commit = GIT_UTIL.get_previous_commit(latest_commit).hexsha
        if GIT_UTIL.has_file_changed(
            changelog_path, latest_commit, previous_commit
        ) or GIT_UTIL.has_file_added(changelog_path, latest_commit, previous_commit):
            logger.info(f"Changelog {changelog_path} has been added/modified")

            current_changelogs = LogFileObject(
                **YmlFile.read_from_local_path(changelog_path)
            ).get_log_entries()

            github_client = Github(login_or_token=github_token)

            pr = github_client.get_repo(DEMISTO_SDK_REPO).get_pull(int(self.pr_number))
            markdown = "Changelog(s) in markdown:\n"
            markdown += "\n".join(
                [changelog.to_string() for changelog in current_changelogs]
            )
            pr.create_issue_comment(markdown)

            logger.info(f"Successfully commented on PR {self.pr_number} the changelog")
        else:
            logger.info(
                f"{changelog_path} has not been changed, not commenting on PR {self.pr_number}"
            )

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

        if self.pr_number:
            pr_num = self.pr_number
        else:
            pr_num = get_pr_number_by_branch(GIT_UTIL.repo.active_branch)

        log = INITIAL_LOG
        log["pr_number"] = int(pr_num)

        with (CHANGELOG_FOLDER / f"{pr_num}.yml").open("w") as f:
            yaml.dump(log, f)

        logger.info(f"Created changelog template at .changelog/{pr_num}.yml")

    """ RELEASE """

    def release(self, branch_name: str) -> None:
        """
        Generates a new CHANGELOG.md file by combining all the individual
        changelog files from the .changelog folder.

        It checks that the PR name matches the release format, reads all the log files,
        compiles them into a CHANGELOG.md, updates CHANGELOG.md,
        clears the .changelog folder, commits and pushes the CHANGELOG.md changes.

        Args:
            branch_name: The git branch name to use for committing/pushing CHANGELOG.md

        """
        if not is_release(self.pr_name):
            raise ValueError(
                "The PR name should match `demisto-sdk release 0.0.0` to start a release."
            )

        # get all log files as `LogFileObject`
        logs = read_log_files()

        # get a dict sorted by type of log entry
        new_log_entries = get_new_log_entries(logs)

        new_changelog = compile_changelog_md(
            branch_name, new_log_entries, read_old_changelog()[1:]
        )

        update_changelog_md(new_changelog)
        logger.info("The changelog.md file has been successfully updated")

        clear_changelogs_folder()

        # commit and push CHANGELOG.md
        commit_and_push(branch_name=branch_name)
        logger.info(f"Combined {len(logs)} changelog files into CHANGELOG.md")

    """ HELPER FUNCTIONS """


def get_pr_number_by_branch(branch_name: str):
    """
    Get the PR number of the current branch from Github

    Args:
        branch_name: the branch name that is assosicated with the PR

    Returns:
        PR number associated with the local branch
    """
    try:
        error_message = (
            "Failed to get PR number from Github, please add the PR number manually"
        )
        repo = Github(verify=False).get_repo(DEMISTO_SDK_REPO)
        branch = GIT_UTIL.repo.active_branch.name
        for pr in repo.get_pulls(state="open", head=branch):
            if pr.head.ref == branch:
                return pr.number
        raise Exception(error_message)
    except Exception as e:
        raise Exception(f"{error_message} error:\n{e}")


def extract_errors(error: str, file_name: Path) -> str:
    """
    Extracts the error messages from the json_errors string.
    """
    error_msg = error.split("\n", 1)
    header_error_msg = f"{error_msg[0][:-len('LogFileObject')] + f'{file_name} file'}"
    return f"<red>{header_error_msg}\n{error_msg[1]}</red>"


def is_changelog_modified() -> bool:
    return (
        "CHANGELOG.md"
        in GIT_UTIL.repo.git.diff("HEAD..origin/master", name_only=True).split()
    )


def is_log_yml_exist(pr_number: str) -> bool:
    return (CHANGELOG_FOLDER / f"{pr_number}.yml").exists()


def validate_log_yml(pr_number: str) -> None:
    """
    - imports the log file that belongs to the current PR by the PR name
    - ensure that the log file added to the PR is valid
      according to the conventions of the 'LogFileObject' model
    """
    if not isinstance(data := get_yaml(CHANGELOG_FOLDER / f"{pr_number}.yml"), dict):
        raise ValueError(f"The {pr_number}.yml log file is not valid")

    try:
        LogFileObject(**data)
    except ValidationError as e:
        logger.error(extract_errors(str(e), CHANGELOG_FOLDER / f"{pr_number}.yml"))
        sys.exit(1)


def read_log_files() -> List[LogFileObject]:
    """
    Get all log files under the .changelog folder,
    in case that one of the logs is not valid, an error is raised
    """
    changelogs: List[LogFileObject] = []
    errors: Dict[Path, str] = {}
    for path in CHANGELOG_FOLDER.iterdir():
        if path.name == "README.md":  # exclude README file
            continue

        if not isinstance(log_file := get_yaml(path), dict):
            raise ValueError(f"{path} is not a valid YAML file")

        try:
            changelogs.append(LogFileObject(**log_file))
        except ValidationError as e:
            errors[path] = str(e)

    if errors:
        for file_path, error in errors.items():
            logger.error(extract_errors(error, file_path))
        raise ValueError("One or more files were found invalid, see logs.")
    return changelogs


def get_new_log_entries(logs: List[LogFileObject]) -> Dict[str, List[LogLine]]:
    """
    Parses each LogFileObject and returns a dictionary classified by the type of log entry
    """
    unreleased_logs: List[LogLine] = []
    for log_file in logs:
        unreleased_logs.extend(log_file.get_log_entries())

    new_log_entries: Dict[str, List[LogLine]] = {}
    for type_ in (unreleased_logs_sorted := bucket(unreleased_logs, lambda x: x.type)):
        new_log_entries[type_] = list(unreleased_logs_sorted[type_])
    return new_log_entries


def read_old_changelog():
    return CHANGELOG_MD_FILE.read_text().splitlines()


def compile_changelog_md(
    release_version: str, new_logs: Dict[str, List[LogLine]], old_changelog: List[str]
) -> str:
    """
    Builds the CHANGELOG.md content in stages
    """
    # The title
    new_changelog = ["# Changelog"]
    # New version (x.x.x)
    new_changelog.append(
        f"## {release_version} ({datetime.now().strftime('%Y-%m-%d')})"
    )
    # Collecting the new log entries in the following order:
    # breaking, feature, fix, internal
    for log_type in (LogType.breaking, LogType.feature, LogType.fix, LogType.internal):
        if logs := new_logs.get(log_type, []):
            new_changelog.append(f"### {log_type.capitalize()}")
            new_changelog.extend(log.to_string() for log in logs)
            new_changelog.append("")  # Add an empty line after each category
    new_changelog.append("")
    # Collecting the old changelog
    new_changelog.extend(old_changelog)
    return "\n".join(new_changelog) + "\n"


def update_changelog_md(new_changelog: str) -> None:
    CHANGELOG_MD_FILE.write_text(new_changelog)


def clear_changelogs_folder() -> None:
    for path in CHANGELOG_FOLDER.iterdir():
        if path.name == "README.md":
            continue
        path.unlink()
    logger.info("Cleanup of `.changelog` folder completed successfully")


def is_release(pr_name: str) -> bool:
    return bool(pr_name is not None and RELEASE_VERSION_REGEX.match(pr_name))


def _validate_branch(pr_number: str) -> None:
    if is_changelog_modified():
        raise ValueError(
            "Do not modify changelog.md\n"
            "Run `sdk-changelog  --init -n <pr number>`"
            " to create a changelog file instead."
        )
    if not is_log_yml_exist(pr_number):
        raise ValueError(
            "Missing changelog file.\n"
            "Run `sdk-changelog  --init -n <pr number>` and fill it."
        )
    validate_log_yml(pr_number)


def commit_and_push(branch_name: str):
    repo = Repo(git_path())
    repo.git.add(".")
    repo.index.commit("Combined all changelog files into CHANGELOG.md")
    remote = repo.remote(name="origin")
    remote.push(branch_name)


main = typer.Typer(
    pretty_exceptions_enable=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


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

pr_number = typer.Option("", "--pr_number", "-n", help="Pull request number")

pr_title = typer.Option(
    "", "--pr_title", "-t", help="Pull request title (used for release)"
)

branch_name = typer.Option(
    None, "--branch_name", "-bn", help="The branch name (use only release)"
)


@main.command()
def changelog_management(
    init: bool = init,
    validate: bool = validate,
    release: bool = release,
    pr_number: str = pr_number,
    pr_name: str = pr_title,
    branch_name: str = branch_name,
):
    pr_name = pr_name
    pr_number = pr_number

    changelog = Changelog(pr_number, pr_name)
    if validate:
        return changelog.validate()
    elif init:
        return changelog.init()
    elif release:
        if not branch_name:
            raise ValueError(
                "You must specify a branch name using --branch_name when using --release"
            )
        return changelog.release(branch_name)
    else:
        raise ValueError(
            "One of the following arguments is required [`--init`, `--validate`, `--release`],"
            "\nrun `demisto-sdk changelog --help` for more information"
        )


if __name__ == "__main__":
    main()
