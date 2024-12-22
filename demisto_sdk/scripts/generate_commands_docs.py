import inspect
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import typer
from typer.main import get_command

from demisto_sdk.__main__ import app

# Initialize Typer app
command_docs = typer.Typer()

EXCLUDED_BRANCHES_REGEX = r"^(master|[0-9]+\.[0-9]+\.[0-9]+)$"


def get_current_branch() -> str:
    """Returns the current Git branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
    )
    return result.stdout.strip()


def get_modified_files() -> List[Path]:
    """
    Returns a list of files modified in the current commit as Path objects.
    If no files are modified, it returns an empty list.
    """
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True
    )
    files = result.stdout.splitlines()
    return [Path(file) for file in files]


def extract_changed_commands(modified_files: List[str]) -> List[str]:
    """Extract command names from modified _setup.py files."""
    return [
        Path(file).stem.replace("_setup", "")
        for file in modified_files
        if file.endswith("_setup.py")
    ]


def get_sdk_command(command_name: str):
    """Retrieve the command object from the Typer app."""
    click_app = get_command(app)
    command = click_app.commands.get(command_name)  # type: ignore[attr-defined]
    if command is None:
        return f"No README found for command: {command_name}"
    return command


def get_command_overview(command_name: str) -> str:
    """Retrieve the overview (docstring) for the command."""
    command = get_sdk_command(command_name)
    if isinstance(command, str):
        return command

    command_func = command.callback
    return inspect.getdoc(command_func) or "No overview provided."


def get_command_options(command_name: str) -> str:
    """Generate the options section for the command."""
    command = get_sdk_command(command_name)
    if isinstance(command, str):
        return command

    options_text = "### Options\n\n"
    for param in command.params:
        param_name = (
            f"--{param.name.replace('_', '-')}"
            if param.param_type_name == "option"
            else param.name
        )
        options_text += (
            f"- **{param_name}**: {param.help or 'No description provided'}\n"
        )
        if param.default is not None:
            options_text += f"  - Default: `{param.default}`\n"
        options_text += "\n"
    return options_text


def update_readme(command_name: str, description: str, options: str):
    """Update or create the README.md file for the command."""
    command_doc_path = Path("commands") / command_name / "README.md"
    command_doc_path.parent.mkdir(parents=True, exist_ok=True)

    # Read or create README content
    if not command_doc_path.exists():
        readme_content = (
            f"## {command_name.capitalize()}\n\n### Overview\n\n### Options\n\n"
        )
    else:
        with command_doc_path.open("r") as f:
            readme_content = f.read()

    # Insert/update Overview and Options sections
    updated_readme = re.sub(
        r"(### Overview\n\n).*?(?=\n###|$)",
        rf"\1{description}\n\n",
        readme_content,
        flags=re.DOTALL,
    )
    updated_readme = re.sub(
        r"(### Options\n\n).*?(?=\n###|$)",
        rf"\1{options}",
        updated_readme,
        flags=re.DOTALL,
    )

    # Write updated content back to README.md
    with command_doc_path.open("w") as f:
        f.write(updated_readme)

    print(f"README.md updated for command: {command_name}")  # noqa: T201


def stage_and_commit_readme(command_name: str):
    """Stage and commit the updated README.md file."""
    readme_file = Path("commands") / command_name / "README.md"
    if readme_file.exists():
        # Stage the README file
        subprocess.run(["git", "add", str(readme_file)])

        # Commit the README file
        commit_message = f"Update README.md for {command_name} command"
        subprocess.run(["git", "commit", "-m", commit_message])


def generate_docs_for_command(command_name: str):
    """Generate documentation for a specific command."""
    description = get_command_overview(command_name)
    options = get_command_options(command_name)
    update_readme(command_name, description, options)
    stage_and_commit_readme(command_name)


@command_docs.command()
def generate_docs(modified_files: Optional[List[Path]] = typer.Argument(None)):
    """
    Generate documentation for the given list of modified files.

    If no files are provided, the script will check Git for modified `_setup.py` files.
    """
    if modified_files:
        modified_files = [str(file) for file in modified_files]
    else:
        modified_files = get_modified_files()

    # Extract changed commands
    changed_commands = extract_changed_commands(modified_files)
    if not changed_commands:
        print("No modified commands detected.")  # noqa: T201
        return

    # Generate documentation for each changed command
    print(f"Generating documentation for modified commands: {changed_commands}")  # noqa: T201
    for command_name in changed_commands:
        generate_docs_for_command(command_name)

    print("Documentation generation and Git commits completed.")  # noqa: T201


@command_docs.command()
def pre_commit():
    """
    Pre-commit hook to generate docs for changed commands.
    """
    # Check if the branch should be excluded
    current_branch = get_current_branch()
    if re.match(EXCLUDED_BRANCHES_REGEX, current_branch):
        print(f"Generate docs pre-commit hook skipped on branch '{current_branch}'")  # noqa: T201
        sys.exit(0)

    # Run the documentation generation
    generate_docs()


if __name__ == "__main__":
    command_docs()
