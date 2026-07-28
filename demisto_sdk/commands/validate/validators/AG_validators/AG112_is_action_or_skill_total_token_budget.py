from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.tools import (
    action_text_fragments,
    count_chars_for_texts,
    skill_text_fragments,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[AgentixAction, AgentixSkill]

ACTION_CHAR_LIMIT = 4000
SKILL_CHAR_LIMIT = 8000

ACTION_COUNTED_FIELDS = "name, description, args schema, and outputs schema"
SKILL_COUNTED_FIELDS = "name, description, and skill body"


class IsActionOrSkillTotalTokenBudgetValidator(BaseValidator[ContentTypes]):
    error_code = "AG112"
    description = (
        "Checks that an AgentixAction or AgentixSkill definition does not exceed "
        f"its character budget (actions: {ACTION_CHAR_LIMIT}, skills: "
        f"{SKILL_CHAR_LIMIT}). For actions this covers the name, description, args "
        "schema, and outputs schema; for skills the name, description, and skill body."
    )
    rationale = (
        "Every action and skill an agent can use is injected into the LLM context. "
        "An oversized definition displaces task data in the context window, degrading "
        "the agent's performance and its ability to select and call items correctly. "
        "The budget is in characters (~4 chars = 1 token) as a proxy for token cost."
    )
    error_message = (
        "The {0} '{1}' is too large: the combined {2} add up to "
        "{3} characters, which exceeds the limit of {4}. Trim these fields."
    )
    related_file_type = [RelatedFileType.SKILL_CONTENT]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            if isinstance(content_item, AgentixAction):
                item_type = "AgentixAction"
                limit = ACTION_CHAR_LIMIT
                counted_fields = ACTION_COUNTED_FIELDS
                fragments = action_text_fragments(content_item)
            else:
                item_type = "AgentixSkill"
                limit = SKILL_CHAR_LIMIT
                counted_fields = SKILL_COUNTED_FIELDS
                fragments = skill_text_fragments(content_item)
            total_chars = count_chars_for_texts(fragments)
            if total_chars > limit:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            item_type,
                            content_item.name,
                            counted_fields,
                            total_chars,
                            limit,
                        ),
                        content_object=content_item,
                    )
                )
        logger.debug(
            f"[{self.error_code}] Finished. Found {len(results)} invalid item(s)."
        )
        return results
