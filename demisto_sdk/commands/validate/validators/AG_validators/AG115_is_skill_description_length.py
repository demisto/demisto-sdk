from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixSkill

DESCRIPTION_MIN_WORDS = 10
DESCRIPTION_MAX_WORDS = 200


class IsSkillDescriptionLengthValidator(BaseValidator[ContentTypes]):
    error_code = "AG115"
    description = (
        "Checks that the AgentixSkill description length is within "
        f"{DESCRIPTION_MIN_WORDS}-{DESCRIPTION_MAX_WORDS} words."
    )
    rationale = (
        "The description is the router matching key. An out-of-range "
        "description causes the wrong skill to fire for unrelated requests."
    )
    error_message = "The AgentixSkill '{0}' has an invalid description: {1}"
    related_field = "description"
    expected_git_statuses = [
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
        GitStatuses.RENAMED,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            description = content_item.description or ""
            word_count = len(description.split())

            problem = ""
            if word_count < DESCRIPTION_MIN_WORDS:
                problem = (
                    f"it has {word_count} words (minimum is {DESCRIPTION_MIN_WORDS})."
                )
            elif word_count > DESCRIPTION_MAX_WORDS:
                problem = (
                    f"it has {word_count} words (maximum is {DESCRIPTION_MAX_WORDS})."
                )

            if problem:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.display_name, problem
                        ),
                        content_object=content_item,
                    )
                )
        return results
