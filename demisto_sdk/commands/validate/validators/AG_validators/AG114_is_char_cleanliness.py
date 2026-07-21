from __future__ import annotations

import re
from typing import Iterable, List, Tuple, Union

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.content_graph.objects.collection import Collection
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[AgentixSkill, AgentixAction, Collection]

# Allowed punctuation per the authoring guide, plus alphanumerics and whitespace.
_ALLOWED_PUNCTUATION = r""".,;:!?'"`~@#$%^&*()\[\]{}\-_+=<>/\\| """
ALLOWED_CHAR_PATTERN = re.compile(
    r"[A-Za-z0-9" + re.escape(_ALLOWED_PUNCTUATION) + r"\t\r\n]"
)

_FENCED_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`]*`")


class IsCharCleanlinessValidator(BaseValidator[ContentTypes]):
    error_code = "AG114"
    description = (
        "Checks that Agentix action, skill, and knowledge definitions contain "
        "only plain ASCII characters across all text fields (name, display "
        "name, description, argument names/descriptions, enum/default values, "
        "and output content). Prose bodies are checked excluding code blocks."
    )
    rationale = (
        "Emojis, decorative Unicode, smart quotes, em-dashes, accented letters, "
        "and non-breaking spaces waste tokens and can confuse the LLM. Use ASCII "
        "substitutes instead (-- for em-dash, -> for arrow, straight quotes)."
    )
    error_message = (
        "The {0} '{1}' contains disallowed non-ASCII characters.\n"
        "Offending field(s):\n{2}\n"
        "Remove emojis, decorative Unicode, smart quotes, em-dashes, and accented "
        "letters, or replace them with ASCII substitutes."
    )
    related_field = "content"
    related_file_type = [RelatedFileType.SKILL_CONTENT]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            offending: List[str] = []
            for field_name, text in collect_text_fields(content_item):
                disallowed = find_disallowed_chars(text)
                if disallowed:
                    chars = " ".join(repr(ch) for ch in disallowed)
                    offending.append(f"  - {field_name}: {chars}")

            if offending:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.content_type.value,
                            content_item.display_name,
                            "\n".join(offending),
                        ),
                        content_object=content_item,
                    )
                )
        logger.debug(
            f"[{self.error_code}] Finished. Found {len(results)} invalid item(s)."
        )
        return results


def strip_code_blocks(text: str) -> str:
    """Remove fenced and inline code so narrative-text checks ignore code samples."""
    without_fenced = _FENCED_CODE_BLOCK.sub(" ", text)
    return _INLINE_CODE.sub(" ", without_fenced)


def find_disallowed_chars(text: str) -> List[str]:
    """Return sorted unique non-ASCII / disallowed characters present in text."""
    return sorted({ch for ch in text if not ALLOWED_CHAR_PATTERN.match(ch)})


def _collect_skill_fields(item: AgentixSkill) -> List[Tuple[str, str]]:
    """Return (field_name, narrative text) pairs for a skill.

    The description and the ``<SKILL_NAME>_skill.md`` body are narrative text, so
    code blocks are stripped before checking.
    """
    fields: List[Tuple[str, str]] = []
    if item.name:
        fields.append(("name", item.name))
    if item.description:
        fields.append(("description", strip_code_blocks(item.description)))
    try:
        body = item.skill_content_file.file_content
    except Exception:
        body = ""
    if body:
        fields.append(("skill_content", strip_code_blocks(body)))
    return fields


def _collect_action_fields(item: AgentixAction) -> List[Tuple[str, str]]:
    """Return (field_name, text) pairs for an action.

    Structured fields (names, enum/default values) are checked verbatim so a
    banned character can never be hidden; the description is narrative text and
    has its code blocks stripped.
    """
    fields: List[Tuple[str, str]] = []
    if item.name:
        fields.append(("name", item.name))
    if item.display_name:
        fields.append(("display_name", item.display_name))
    if item.description:
        fields.append(("description", strip_code_blocks(item.description)))
    for arg in item.args or []:
        if arg.name:
            fields.append((f"arg '{arg.name}' name", arg.name))
        if arg.description:
            fields.append(
                (
                    f"arg '{arg.name}' description",
                    strip_code_blocks(arg.description),
                )
            )
        if arg.type:
            fields.append((f"arg '{arg.name}' type", arg.type))
        if arg.default_value:
            fields.append((f"arg '{arg.name}' default_value", arg.default_value))
    for output in item.outputs or []:
        if output.name:
            fields.append((f"output '{output.name}' name", output.name))
        if output.description:
            fields.append(
                (
                    f"output '{output.name}' description",
                    strip_code_blocks(output.description),
                )
            )
        if output.type:
            fields.append((f"output '{output.name}' type", output.type))
    return fields


def _collect_collection_fields(item: Collection) -> List[Tuple[str, str]]:
    """Return (field_name, text) pairs for a knowledge (Collection) item.

    Collection has a minimal, evolving schema, so text fields are gathered
    defensively via ``getattr``.
    """
    fields: List[Tuple[str, str]] = []
    for field_name in ("name", "display_name", "description"):
        value = getattr(item, field_name, None)
        if isinstance(value, str) and value:
            fields.append((field_name, value))
    return fields


def collect_text_fields(item: ContentTypes) -> List[Tuple[str, str]]:
    """Dispatch to the per-type field collector."""
    if isinstance(item, AgentixSkill):
        return _collect_skill_fields(item)
    if isinstance(item, AgentixAction):
        return _collect_action_fields(item)
    return _collect_collection_fields(item)


# Backward-compatible alias for the previous skill-only class name.
IsSkillCharCleanlinessValidator = IsCharCleanlinessValidator
