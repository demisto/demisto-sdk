from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixSkill


class IsSkillContentFileExistsValidator(BaseValidator[ContentTypes]):
    error_code = "AG111"
    description = "Checks that the AgentixSkill follows the required package format (a 'skill.md' body file next to 'metadata.yml')."
    error_message = (
        "The AgentixSkill '{0}' is missing its content file. "
        "Please create a file named 'skill.md' in the skill's directory "
        "('Packs/<PackName>/AgentixSkills/{1}/skill.md')."
    )
    related_field = "content"
    rationale = (
        "An AgentixSkill package must contain a 'metadata.yml' schema file and a "
        "'skill.md' body file in the same directory under 'AgentixSkills/'. The "
        "skill body is merged into the 'content' field at upload time, so the "
        "'skill.md' file is required for the skill to be valid."
    )
    related_file_type = [RelatedFileType.SKILL_CONTENT]
    expected_git_statuses = [
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
        GitStatuses.RENAMED,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.display_name,
                    content_item.path.parent.name,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.skill_content_file.exist
        ]
