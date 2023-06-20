from typing import Optional

from demisto_sdk.commands.common.tools import write_yml

CHANGELOG_PATH = "Utils/changelog/"

changelog_template = {
    "type": None,  # fix, feature, breaking
    "description": None,  # string
}


def create_changelog_yml_file(pr_number: Optional[str]) -> None:
    if not pr_number:
        pr_number = None  # need to added a random number

    write_yml(f"{CHANGELOG_PATH}{pr_number}.yml", changelog_template)
