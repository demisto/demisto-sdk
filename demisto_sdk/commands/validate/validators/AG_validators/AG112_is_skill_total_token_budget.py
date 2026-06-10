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

# Token estimation heuristic from the skill authoring guide: ~4 chars per token.
CHARS_PER_TOKEN = 4
SKILL_TOKEN_LIMIT = 2000


def estimate_tokens(text: str) -> int:
    """Estimate token count using the guide's ~4-chars-per-token heuristic."""
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


class IsSkillTotalTokenBudgetValidator(BaseValidator[ContentTypes]):
    error_code = "AG112"
    description = (
        "Checks that the AgentixSkill 'SKILL_NAME_skill.md' body does not exceed "
        f"{SKILL_TOKEN_LIMIT} estimated tokens."
    )
    rationale = (
        "Oversized skill files displace task data in the LLM context window, "
        "degrading the agent's performance."
    )
    error_message = (
        "The AgentixSkill '{0}' skill body file is too large: an estimated "
        f"{{1}} tokens (limit is {SKILL_TOKEN_LIMIT}). Trim the skill body."
    )
    related_field = "content"
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
            body = content_item.skill_content_file.file_content
            total_tokens = estimate_tokens(body)
            logger.debug(
                f"[{self.error_code}] Skill '{content_item.display_name}': "
                f"estimated {total_tokens} tokens (limit {SKILL_TOKEN_LIMIT})."
            )
            if total_tokens > SKILL_TOKEN_LIMIT:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.display_name, total_tokens
                        ),
                        content_object=content_item,
                    )
                )
        logger.debug(
            f"[{self.error_code}] Finished. Found {len(results)} invalid item(s)."
        )
        return results
