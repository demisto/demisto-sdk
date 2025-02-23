import argparse
import os
from pathlib import Path
import sys

from demisto_sdk.commands.common.constants import CONTENT_REPO
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.scripts.changelog.changelog import Changelog


def comment_changelog_on_pr(pr_num: int, latest_commit: str, github_token: str):
    try:
        Changelog(pr_num).comment(latest_commit, github_token)
        sys.exit(0)
    except Exception:
        logger.exception("Couldn't comment on the changelog.")
        sys.exit(1)
        


def comment_validate_summary(github_token: str, pr_num: int) -> None:
    """
    Comment on the PR

    Checks the following:
        - If the changelog file has been added in latest commit OR If the changelog file has been
            modified between the last two commits.

    """
    validate_summary_msg = obtain_validate_summary_msg()
    
    from github import Github

    github_client = Github(login_or_token=github_token)

    pr = github_client.get_repo(CONTENT_REPO).get_pull(int(pr_num))
    pr.create_issue_comment(validate_summary_msg)

    logger.info(f"Successfully commented on PR {pr_num} the validate summary.")


def obtain_validate_summary_msg() -> str:
    validate_summary_msg = ""
    if (artifacts_folder := os.getenv("ARTIFACTS_FOLDER")) and Path(
            artifacts_folder
        ).exists():
            artifacts_validate_summary_path = Path(
                f"{artifacts_folder}/validate_summary.txt"
            )
            logger.info(f"reading from the validate summary results to a txt file at {artifacts_validate_summary_path}.")
            with open(artifacts_validate_summary_path, "ר") as f:
                validate_summary_msg = f.read()
    else:
        raise Exception(f"could not find validate summary file.")
    
    if not validate_summary_msg:
        raise Exception("validate_summary_msg is empty.")

def comment_validate_summary_on_pr(pr_num: int, github_token: str):
    try:
        comment_validate_summary(github_token, pr_num)
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
        "-vs", "--validate_summary", help="Boolean.Whether to run validate summary", required=False, action=argparse.BooleanOptionalAction
    )

    return parser.parse_args()


def main():
    options = arguments_handler()
    pr_num = options.pr_number
    latest_commit = options.latest_commit
    github_token = options.github_token
    validate_summary = options.validate_summary
    if validate_summary:
        comment_validate_summary_on_pr(pr_num, latest_commit)
    else:
        comment_changelog_on_pr(pr_num, latest_commit, github_token)


if __name__ == "__main__":
    main()
