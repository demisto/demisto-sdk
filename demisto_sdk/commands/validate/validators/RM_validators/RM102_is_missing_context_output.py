from __future__ import annotations

import re
from typing import Iterable, List, Set

from ordered_set import OrderedSet

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


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
        invalid_content_items: List[ValidationResult] = []
        count = 0
        for content_item in content_items:
            discrepancies = []
            for command in content_item.commands:
                yml_context_paths = self.get_command_context_paths_from_yml(command)
                readme_context_paths = self.get_command_context_path_from_readme_file(
                    command.name, content_item.readme.file_content
                )
                if readme_context_paths == set():
                    continue
                missing_in_yml = OrderedSet(readme_context_paths - yml_context_paths)
                missing_in_readme = OrderedSet(yml_context_paths - readme_context_paths)

                if missing_in_yml or missing_in_readme:
                    count += 1
                    discrepancy = f"{command.name}:\n"
                    if missing_in_yml:
                        discrepancy += f"The following outputs are missing from yml: {', '.join(missing_in_yml)}\n"
                    if missing_in_readme:
                        discrepancy += f"The following outputs are missing from readme: {', '.join(missing_in_readme)}\n"
                    discrepancies.append(discrepancy)
            if discrepancies:
                invalid_content_items.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            discrepancies="\n".join(discrepancies)
                        ),
                        content_object=content_item,
                    )
                )

        return invalid_content_items

    def get_command_context_paths_from_yml(self, command) -> Set[str]:
        return {output.contextPath for output in command.outputs if output.contextPath}

    def compare_context_paths(
        self, yml_paths: Set[str], readme_paths: Set[str]
    ) -> Set[str]:
        return readme_paths - yml_paths

    def get_command_context_path_from_readme_file(
        self, command_name: str, readme_content: str
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
        command_section = re.findall(command_section_pattern, readme_content, re.DOTALL)

        if not command_section:
            return set()
        if not command_section[0].endswith("###"):
            command_section[0] += (
                "###"  # mark end of file so last pattern of regex will be recognized.
            )
        # Pattern to get the context output section
        context_section_pattern = r"\| *\*\*Path\*\* *\| *\*\*Type\*\* *\| *\*\*Description\*\* *\|.(.*?)#{3,5}"
        context_section = re.findall(
            context_section_pattern, command_section[0], re.DOTALL
        )

        if not context_section:
            return set()

        # Pattern to get the context paths
        context_path_pattern = r"\| *(\S.*?\S) *\| *[^\|]* *\| *[^\|]* *\|"
        context_paths = set(
            re.findall(context_path_pattern, context_section[0], re.DOTALL)
        )

        # Remove the header line if present
        return {path for path in context_paths if path.replace("-", "")}
