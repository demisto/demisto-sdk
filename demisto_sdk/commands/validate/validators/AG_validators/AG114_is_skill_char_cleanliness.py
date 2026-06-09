from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixSkill

# Allowed punctuation per the authoring guide, plus alphanumerics and whitespace.
_ALLOWED_PUNCTUATION = r""".,;:!?'"`~@#$%^&*()\[\]{}\-_+=<>/\\| """
ALLOWED_CHAR_PATTERN = re.compile(
    r"[A-Za-z0-9" + re.escape(_ALLOWED_PUNCTUATION) + r"\t\r\n]"
)

_FENCED_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`]*`")


def strip_code_blocks(text: str) -> str:
    """Remove fenced and inline code so prose-only checks ignore code samples."""
    without_fenced = _FENCED_CODE_BLOCK.sub(" ", text)
    return _INLINE_CODE.sub(" ", without_fenced)


def find_disallowed_chars(prose: str) -> List[str]:
    """Return sorted unique non-ASCII / disallowed characters present in prose."""
    return sorted({ch for ch in prose if not ALLOWED_CHAR_PATTERN.match(ch)})


class IsSkillCharCleanlinessValidator(BaseValidator[ContentTypes]):
    error_code = "AG114"
    description = (
        "Checks that the AgentixSkill prose (description and 'skill.md' body, "
        "excluding code blocks) contains only ASCII characters."
    )
    rationale = (
        "Emojis, decorative Unicode, and ASCII art waste tokens and can confuse "
        "the LLM. Prose must use plain ASCII text only."
    )
    error_message = (
        "The AgentixSkill '{0}' contains disallowed non-ASCII characters: {1}. "
        "Remove emojis, decorative Unicode, and ASCII art."
    )
    related_field = "content"
    related_file_type = [RelatedFileType.SKILL_CONTENT]
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
            body = content_item.skill_content_file.file_content
            prose = strip_code_blocks(f"{content_item.description or ''}\n{body}")
            disallowed = find_disallowed_chars(prose)
            if disallowed:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.display_name,
                            " ".join(repr(ch) for ch in disallowed),
                        ),
                        content_object=content_item,
                    )
                )
        return results
