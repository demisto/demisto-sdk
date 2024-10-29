import inspect
from pathlib import Path

from typer.main import get_command

# Assuming this is your main Typer app
from demisto_sdk.__main__ import app


def generate_docs_for_commands(output_dir: str):
    """Generate markdown docs for all commands in the Typer app."""

    # Ensure the output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get the underlying Click command for Typer app
    click_app = get_command(app)

    # Iterate over registered commands in the Click context
    for command_name, command in click_app.commands.items():
        # Access the callback function and other attributes
        command_func = command.callback  # The function itself (the callback)
        docstring = (
            inspect.getdoc(command_func) if command_func else "No description provided"
        )
        help_text = command.help or "No help text provided"

        # Collecting options/flags information
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

        # Save each command's docs as a markdown file
        doc_file = output_path / f"{command_name}.md"
        with doc_file.open("w") as f:
            f.write(f"# {command_name} Command\n\n")
            f.write(f"## Description\n{docstring}\n\n")
            f.write(f"## Help Text\n```\n{help_text}\n```\n\n")
            f.write(options_text)

        print(f"Documentation generated for command: {command_name}")


# Specify the output directory where the docs should be saved
generate_docs_for_commands("docs/commands")
