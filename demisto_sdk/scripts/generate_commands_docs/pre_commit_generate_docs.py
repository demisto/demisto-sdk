import os
import re
import subprocess
import sys
from pathlib import Path

EXCLUDED_BRANCHES_REGEX = r"^(master|[0-9]+\.[0-9]+\.[0-9]+)$"


def get_current_branch():
    """Returns the current Git branch name."""
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
    return result.stdout.strip()


def get_modified_files():
    """Returns a list of files modified in the current commit."""
    result = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True)
    return result.stdout.splitlines()


def extract_changed_commands(modified_files):
    """Extract command names from modified _setup.py files."""
    changed_commands = []
    for file in modified_files:
        if file.endswith("_setup.py"):
            command_name = Path(file).stem.replace("_setup", "")
            changed_commands.append(command_name)
    return changed_commands


def main():
    # Check if the branch should be excluded
    current_branch = get_current_branch()
    if re.match(EXCLUDED_BRANCHES_REGEX, current_branch):
        print(f"Pre-commit hook skipped on branch '{current_branch}'")
        sys.exit(0)

    # Get the list of modified files
    modified_files = get_modified_files()

    # Filter for _setup.py files to determine which commands changed
    changed_commands = extract_changed_commands(modified_files)
    if not changed_commands:
        print("No modified _setup.py files found. Skipping documentation generation.")
        sys.exit(0)

    # Run the documentation generation script with all changed commands
    print(f"Generating documentation for modified commands: {changed_commands}")
    subprocess.run([sys.executable, "generate_docs.py", *changed_commands])

    # Stage the newly generated or updated README files for each command
    for command_name in changed_commands:
        readme_file = Path("demisto-sdk/commands") / command_name / "README.md"
        if readme_file.exists():
            subprocess.run(["git", "add", str(readme_file)])

    print("Pre-commit hook completed successfully.")


if __name__ == "__main__":
    main()
