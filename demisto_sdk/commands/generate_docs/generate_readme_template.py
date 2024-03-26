from pathlib import Path

from demisto_sdk.commands.generate_docs.readme_templates import README_TEMPLATES


def generate_readme_template(input_path: Path, readme_template: str):
    with open(input_path, "a") as file_object:
        template = README_TEMPLATES.get(readme_template, "")
        if not template:
            raise Exception(
                f"[red]Template type {readme_template} is not supported. Please select one of: {list(README_TEMPLATES.keys())}[/red]"
            )
        file_object.write(template)
