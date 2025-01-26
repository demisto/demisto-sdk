#!/usr/bin/env python3

import inspect
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Union

import typer
from typer.main import get_command

os.environ["DEMISTO_SDK_IGNORE_CONTENT_WARNING"] = "True"

from demisto_sdk.__main__ import app

# Initialize Typer app
docs_app = typer.Typer()

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


def extract_changed_commands(modified_files: List[Union[str, Path]]) -> List[str]:
    """
    Extract command names from modified _setup.py files.
    Args:
        modified_files (List): The list of the modified _setup.py files.
    """
    return [
        Path(file).stem.replace("_setup", "").replace("_", "-")
        for file in modified_files
        if str(file).endswith("_setup.py")
    ]


def get_sdk_command(command_name: str) -> Union[str, object]:
    """
    Retrieve the command object from the Typer app.
    Args:
        command_name (str): The command name e.g. upload.
    """
    click_app = get_command(app)
    command = click_app.commands.get(command_name)  # type: ignore[attr-defined]
    if command is None:
        return f"No README found for command: {command_name}"
    return command


def get_command_overview(command_name: str) -> str:
    """
    Retrieve the overview (docstring) for the command.
    Args:
        command_name (str): The command name e.g. upload.
    """
    command = get_sdk_command(command_name)

    if isinstance(command, str):
        typer.secho(f"Error: {command}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    command_func = command.callback  # type: ignore[attr-defined]
    return inspect.getdoc(command_func) or "No overview provided."


def get_command_options(command_name: str) -> str:
    """
    Generate the options section for the command.
    Args:
        command_name (str): The command name e.g. upload.
    """
    command = get_sdk_command(command_name)
    if isinstance(command, str):
        return command

    options_text = ""
    for param in command.params:  # type: ignore[attr-defined]
        param_name = (
            f"--{param.name.replace('_', '-')}"
            if param.param_type_name == "option"
            else param.name
        )
        options_text += f"- **{param_name}**: {param.help or ''}\n"
        if param.default is not None:
            options_text += f"  - Default: `{param.default}`\n"
        options_text += "\n"
    return options_text


def update_readme(command_name: str, overview: str, options: str) -> None:
    """
    Update or create the README.md file for the command.
    Args:
        command_name (str): The name of the command for which to generate documentation e.g. upload.
        overview (str): The command overview (docstring of the command).
        options (str): Options for the command.
    """
    # Normalize the command name to match the folder naming convention
    normalized_command_name = command_name.replace("-", "_")

    command_doc_path = (
        Path("demisto_sdk") / "commands" / normalized_command_name / "README.md"
    )
    command_doc_path.parent.mkdir(parents=True, exist_ok=True)

    # Read the current README content if it exists, otherwise initialize it
    if command_doc_path.exists():
        with command_doc_path.open("r") as f:
            readme_content = f.read()
    else:
        readme_content = f"## {command_name}\n"

    # Function to update or insert a section in the README
    def update_section(header: str, content: str, readme: str) -> str:
        """
        Update or add a section to the README content.

        Args:
            header (str): The title of the section to update or add (e.g., "Overview" or "Options").
            content (str): The content to insert or replace in the specified section.
            readme (str): The current README content as a string.

        Returns:
            str: The updated README content with the specified section added or replaced.
        """
        section_header = f"### {header}"

        # Check if the section exists
        if section_header in readme:
            # Replace the content of the existing section
            start_index = readme.find(section_header) + len(section_header)
            end_index = (
                readme.find("###", start_index)
                if "###" in readme[start_index:]
                else len(readme)
            )
            readme = (
                readme[:start_index] + f"\n\n{content.strip()}\n" + readme[end_index:]
            )
        else:
            # Append the new section
            readme = readme.strip() + f"\n\n{section_header}\n\n{content.strip()}"

        return readme

    # Update or add the Overview and Options sections
    updated_readme = update_section("Overview", overview, readme_content)
    updated_readme = update_section("Options", options, updated_readme)

    # Write the updated or new README file
    with command_doc_path.open("w") as f:
        f.write(updated_readme)

    print(f"README.md updated for command: {command_name}")  # noqa: T201


def generate_docs_for_command(command_name: str) -> None:
    """
    Generate documentation for a specific command.
    Args:
        command_name (str): The name of the command for which to generate documentation e.g. upload.
    """
    overview = get_command_overview(command_name)
    options = get_command_options(command_name)
    update_readme(command_name, overview, options)


def generate_docs(modified_files: Optional[List[Path]] = typer.Argument(None)) -> None:
    """
    Generate documentation for the given list of modified files.
    If no files are provided, the script will check Git for modified `_setup.py` files.
    Args:
        modified_files (Optional[List[Path]]): A list of file paths representing the modified files to process.
    """
    # Check if modified_files is None, and if so, get the modified files from git
    if not modified_files:
        modified_files = get_modified_files()
    else:
        # Ensure that modified_files is a list of Path objects
        modified_files = [Path(file) for file in modified_files]
    changed_commands = extract_changed_commands(modified_files)  # type: ignore[arg-type]
    if not changed_commands:
        print("No modified commands detected.")  # noqa: T201
        return

    print(f"Generating documentation for modified commands: {changed_commands}")  # noqa: T201
    for command_name in changed_commands:
        generate_docs_for_command(command_name)

    print("Documentation generation and Git commits completed.")  # noqa: T201


@docs_app.command()
def pre_commit() -> None:
    """
    Pre-commit hook to generate docs for changed commands.
    """
    current_branch = get_current_branch()
    if re.match(EXCLUDED_BRANCHES_REGEX, current_branch):
        print(f"Generate docs pre-commit hook skipped on branch '{current_branch}'")  # noqa: T201
        sys.exit(0)

    # Get the modified files (no need to pass as an argument)
    modified_files = get_modified_files()

    # Call generate_docs with the list of modified files
    generate_docs(modified_files)


def main():
    docs_app()


if __name__ == "__main__":
    main()
