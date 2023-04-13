import logging

from demisto_sdk.commands.generate_docs.readme_templates import README_TEMPLATES

logger = logging.getLogger("demisto-sdk")


def generate_readme_template(input_path: str, readme_template: str):
    with open(input_path, "a") as file_object:
        template = README_TEMPLATES.get(readme_template, "")
        if not template:
            logger.error(
                f"[red]Template type {readme_template} is not supported.[/red]"
            )
            return 1
        file_object.write(template)
