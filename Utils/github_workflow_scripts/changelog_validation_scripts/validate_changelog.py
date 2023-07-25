


import argparse
import sys

from demisto_sdk.commands.changelog.changelog import Changelog


def validate_changelog_and_logs(pr_num: str, pr_name: str) -> bool:
    changelog = Changelog(pr_num, pr_name)
    if changelog.validate():
        sys.exit(0)
    sys.exit(1)
    
    
    

def arguments_handler():
    """Validates and parses script arguments.

    Returns:
       Namespace: Parsed arguments object.

    """
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-pn", "--pr_number", help="The PR number.", required=True)
    parser.add_argument("-pt", "--pr_title", help="The PR title.", required=False)
    
    return parser.parse_args()


def main():
    options = arguments_handler()
    pr_num = options.pr_number
    pr_name = options.pr_title
    validate_changelog_and_logs(pr_num, pr_name)


if __name__ == "__main__":
    main()
