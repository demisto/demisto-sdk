import re
import subprocess
import sys
from pathlib import Path
from typing import List

from demisto_sdk.scripts.generate_commands_docs.generate_commands_docs import (
    generate_docs_for_command,
)

EXCLUDED_BRANCHES_REGEX = r"^(master|[0-9]+\.[0-9]+\.[0-9]+)$"


def get_current_branch() -> str:
    """Returns the current Git branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
    )
    return result.stdout.strip()


def get_modified_files() -> List[str]:
    """Returns a list of files modified in the current commit."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True
    )
    return result.stdout.splitlines()


def extract_changed_commands(modified_files: List[str]) -> List[str]:
    """Extract command names from modified _setup.py files."""
    return [
        Path(file).stem.replace("_setup", "")
        for file in modified_files
        if file.endswith("_setup.py")
    ]


def main() -> None:
    # Check if the branch should be excluded
    current_branch = get_current_branch()
    if re.match(EXCLUDED_BRANCHES_REGEX, current_branch):
        print(f"Generate docs pre-commit hook skipped on branch '{current_branch}'")  # noqa: T201
        sys.exit(0)

    # Get the list of modified files
    modified_files = get_modified_files()

    # Filter for _setup.py files to determine which commands changed
    changed_commands = extract_changed_commands(modified_files)

    # Run the documentation generation script with all changed commands
    print(f"Generating documentation for modified commands: {changed_commands}")  # noqa: T201
    for command_name in changed_commands:
        generate_docs_for_command(command_name)

    # Stage the newly generated or updated README files for each command
    for command_name in changed_commands:
        readme_file = Path("demisto-sdk/commands") / command_name / "README.md"
        if readme_file.exists():
            subprocess.run(["git", "add", str(readme_file)])

    print("Pre-commit hook completed successfully.")  # noqa: T201


if __name__ == "__main__":
    main()
