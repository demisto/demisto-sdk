import argparse
import sys

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.scripts.changelog.changelog import Changelog


def validate_changelog_and_logs(pr_num: str, pr_name: str) -> bool:
    try:
        Changelog(pr_num, pr_name).validate()
        sys.exit(0)
    except Exception:
        logger.exception("Changelog validation failed.")
        sys.exit(1)


def arguments_handler():
    """Validates and parses script arguments.

    Returns:
       Namespace: Parsed arguments object.

    """
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-n", "--pr-number", help="The PR number.", required=True)
    parser.add_argument("-t", "--pr-title", help="The PR title.", required=False)

    return parser.parse_args()


def main():
    options = arguments_handler()
    pr_num = options.pr_number
    pr_name = options.pr_title
    validate_changelog_and_logs(pr_num, pr_name)


if __name__ == "__main__":
    main()
