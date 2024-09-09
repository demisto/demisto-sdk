from __future__ import annotations

import re
from typing import Iterable, List, NamedTuple, Set

from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class Discrepancy(NamedTuple):
    command_name: str
    missing_in_yml: Set[str]
    missing_in_readme: Set[str]


class IsMissingContextOutputValidator(BaseValidator[ContentTypes]):
    error_code = "RM102"
    description = "Validates that all context outputs defined in the README file are present in the YML file, and vice versa."
    rationale = "Ensuring consistency between the README and YML files helps maintain accurate documentation and prevents discrepancies."
    error_message = "Find discrepancy for the following commands:\n{discrepancies}"
    related_field = "outputs"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self._format_error_message(discrepancies),
                content_object=content_item,
            )
            for content_item in content_items
            if (discrepancies := self._get_discrepancies(content_item))
        ]

    def _get_discrepancies(self, content_item: ContentTypes) -> List[Discrepancy]:
        discrepancies = []
        for command in content_item.commands:
            yml_context_paths = get_command_context_paths_from_yml(command)
            readme_context_paths = get_command_context_path_from_readme_file(
                command.name, content_item.readme.file_content
            )
            if not readme_context_paths:
                continue
            missing_in_yml = readme_context_paths - yml_context_paths
            missing_in_readme = yml_context_paths - readme_context_paths
            if missing_in_yml or missing_in_readme:
                discrepancies.append(
                    Discrepancy(command.name, missing_in_yml, missing_in_readme)
                )
        return discrepancies

    def _format_error_message(self, discrepancies: List[Discrepancy]) -> str:
        formatted_discrepancies = []
        for disc in discrepancies:
            msg = f"{disc.command_name}:\n"
            if disc.missing_in_yml:
                msg += f"The following outputs are missing from yml: {', '.join(disc.missing_in_yml)}\n"
            if disc.missing_in_readme:
                msg += f"The following outputs are missing from readme: {', '.join(disc.missing_in_readme)}\n"
            formatted_discrepancies.append(msg)
        return self.error_message.format(
            discrepancies="\n".join(formatted_discrepancies)
        )


def get_command_context_paths_from_yml(command: Command) -> Set[str]:
    return {output.contextPath for output in command.outputs if output.contextPath}


def get_command_context_path_from_readme_file(
    command_name: str, readme_content: str
) -> Set[str]:
    """
    Extracts context paths from the command section in the README content using regex.

    Args:
        command_name (str): The name of the command to search for.
        readme_content (str): The content of the README file.

    Returns:
        Set[str]: A set of context paths found in the command section.
    """
    readme_content += (
        "### "  # mark end of file so last pattern of regex will be recognized.
    )

    # Gets all context path in the relevant command section from README file
    command_section_pattern = rf" Base Command..`{command_name}`.(.*?)\n### "
    command_section: List[str] = re.findall(
        command_section_pattern, readme_content, re.DOTALL
    )

    if not command_section:
        return set()
    if not command_section[0].endswith("###"):
        command_section[0] += (
            "###"  # mark end of command so last pattern of regex will be recognized.
        )
    # Pattern to get the context output section
    context_section_pattern = (
        r"\| *\*\*Path\*\* *\| *\*\*Type\*\* *\| *\*\*Description\*\* *\|.(.*?)#{3,5}"
    )
    context_section = re.findall(context_section_pattern, command_section[0], re.DOTALL)

    if not context_section:
        return set()

    # Pattern to get the context paths
    context_path_pattern = r"\| *(\S.*?\S) *\| *[^\|]* *\| *[^\|]* *\|"
    context_paths = set(re.findall(context_path_pattern, context_section[0], re.DOTALL))

    # Remove the header line if present
    return {path for path in context_paths if path.replace("-", "")}
