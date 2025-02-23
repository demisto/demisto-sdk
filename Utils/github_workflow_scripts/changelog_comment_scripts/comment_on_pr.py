import argparse
import sys

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.scripts.changelog.changelog import Changelog


def comment_changelog_on_pr(pr_num: int, latest_commit: str, github_token: str):
    try:
        comment_validate_summary(latest_commit, github_token, pr_num)
        sys.exit(0)
    except Exception:
        logger.exception("Couldn't comment on the changelog.")
        sys.exit(1)
        


def comment_validate_summary(self, latest_commit: str, github_token: str, pr_num: int) -> None:
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
        

def comment_validate_summary_on_pr(pr_num: int, latest_commit: str, github_token: str):
    try:
        Changelog(pr_num).comment(latest_commit, github_token)
        sys.exit(0)
    except Exception:
        logger.exception("Couldn't comment validate summary on the PR.")
        sys.exit(1)


def arguments_handler():
    """Validates and parses script arguments.

    Returns:
       Namespace: Parsed arguments object.

    """
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "-n", "--pr-number", help="The PR number.", required=True, type=int
    )
    parser.add_argument(
        "-lt",
        "--latest_commit",
        help="The commit number that triggered the workflow.",
        required=True,
    )
    parser.add_argument(
        "-ght", "--github_token", help="The token for Github-Api", required=True
    )
    parser.add_argument(
        "-vs", "--validate_summary", help="Whether to run validate summary", required=False
    )

    return parser.parse_args()


def main():
    options = arguments_handler()
    pr_num = options.pr_number
    latest_commit = options.latest_commit
    github_token = options.github_token
    validate_summary = options.validate_summary
    if validate_summary:
        comment_validate_summary_on_pr(pr_num, latest_commit, github_token)
    else:
        comment_changelog_on_pr(pr_num, latest_commit, github_token)


if __name__ == "__main__":
    main()
