import inspect
import sys
from pathlib import Path
from typing import List

from typer.main import get_command

from demisto_sdk.__main__ import app


def extract_changed_commands(modified_files: List[str]) -> List[str]:
    """Extract the command names from the list of modified files."""
    changed_commands = []
    for file in modified_files:
        # Check if the modified file ends with '_setup.py'
        if file.endswith("_setup.py"):
            command_name = Path(file).stem.replace("_setup", "")
            changed_commands.append(command_name)
    return changed_commands


def get_sdk_command(command_name: str):
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
    """Update the README.md file for the command with the given description and options."""
    command_doc_path = Path("demisto_sdk/commands") / command_name / "README.md"

    if not command_doc_path.exists():
        print(f"README.md not found for command: {command_name}")  # noqa: T201
        return

    # Read the existing README.md
    with command_doc_path.open("r") as f:
        readme_content = f.read()

    # Update the Description section
    description_start = readme_content.find("## Overview")
    if description_start != -1:
        description_end = readme_content.find(
            "##", description_start + len("## Overview")
        )
        if description_end == -1:
            description_end = len(readme_content)
        updated_readme = (
            readme_content[:description_start]
            + f"## Overview\n{description}\n\n"
            + readme_content[description_end:]
        )
    else:
        updated_readme = f"{readme_content}\n## Overview\n{description}\n\n"

    # Update the Options section
    options_start = updated_readme.find("### Options")
    if options_start != -1:
        options_end = updated_readme.find("##", options_start + len("### Options"))
        if options_end == -1:
            options_end = len(updated_readme)
        updated_readme = (
            updated_readme[:options_start] + options + updated_readme[options_end:]
        )
    else:
        updated_readme += "\n" + options

    # Write the updated content back into the README.md
    with command_doc_path.open("w") as f:
        f.write(updated_readme)

    print(f"Overview and options section updated for command: {command_name}")  # noqa: T201


def generate_docs_for_command(command_name: str):
    """Generate documentation for a specific command."""
    description = get_command_overview(command_name)
    options = get_command_options(command_name)
    update_readme(command_name, description, options)


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_docs.py <modified_file1> <modified_file2> ...")  # noqa: T201
        sys.exit(1)

    # Receive the list of modified files from command-line arguments
    modified_files = sys.argv[1:]
    changed_commands = extract_changed_commands(modified_files)

    # Generate documentation for each modified command
    for command_name in changed_commands:
        generate_docs_for_command(command_name)


if __name__ == "__main__":
    main()
