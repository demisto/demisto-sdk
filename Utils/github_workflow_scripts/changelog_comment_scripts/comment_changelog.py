import argparse
import sys

from demisto_sdk.commands.common.loguru_logger import logger
from demisto_sdk.scripts.changelog.changelog import Changelog


def comment_changelog_on_pr(pr_num: int, latest_commit: str, github_token: str):
    try:
        Changelog(pr_num).comment(latest_commit, github_token)
        sys.exit(0)
    except Exception:
        logger.exception("Couldn't comment on the changelog.")
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

    return parser.parse_args()


def main():
    options = arguments_handler()
    pr_num = options.pr_number
    latest_commit = options.latest_commit
    github_token = options.github_token
    comment_changelog_on_pr(pr_num, latest_commit, github_token)


if __name__ == "__main__":
    main()
