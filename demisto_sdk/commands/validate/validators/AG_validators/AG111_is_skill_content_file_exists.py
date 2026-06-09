from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.logger import logger
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
        "('Packs/{2}/AgentixSkills/{1}/skill.md')."
    )
    related_field = "content"
    rationale = (
        "An AgentixSkill package must contain a 'metadata.yml' schema file and a "
        "'skill.md' body file in the same directory under 'AgentixSkills/'. The "
        "skill body is merged into the 'content' field at upload time, so the "
        "'skill.md' file is required for the skill to be valid."
    )
    related_file_type = [RelatedFileType.SKILL_CONTENT]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        content_items = list(content_items)
        logger.debug(
            f"[{self.error_code}] Running on {len(content_items)} AgentixSkill item(s)."
        )
        results: List[ValidationResult] = []
        for content_item in content_items:
            exists = content_item.skill_content_file.exist
            logger.debug(
                f"[{self.error_code}] Skill '{content_item.display_name}': "
                f"skill.md exists={exists}."
            )
            if not exists:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.display_name,
                            content_item.path.parent.name,
                            content_item.pack_name,
                        ),
                        content_object=content_item,
                    )
                )
        logger.debug(
            f"[{self.error_code}] Finished. Found {len(results)} invalid item(s)."
        )
        return results
