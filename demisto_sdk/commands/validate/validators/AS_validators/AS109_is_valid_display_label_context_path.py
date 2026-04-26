from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, Iterable, List, Set, Tuple, Union

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Playbook]

# Extracts context keys from ${...} placeholders, e.g. ${issue.id} -> "issue.id"
_CONTEXT_KEY_RE = re.compile(r"\$\{([^}]+)\}")

# Matches dot-separated identifiers, e.g. "PaloAltoNetworksXQL.GenericQuery.results"
# Used to capture root values in complex field references.
_DOT_PATH_RE = re.compile(r"[A-Za-z_]\w*(?:\.\w+)+")


class IsValidDisplayLabelContextPathValidator(BaseValidator[ContentTypes]):
    error_code = "AS109"
    description = (
        "Validate that context keys referenced in displayLabel fields "
        "are actually used in other tasks within the same playbook."
    )
    rationale = (
        "In autonomous packs (managed: true, source: 'autonomous'), playbook task "
        "displayLabel fields should only reference context keys that are used in "
        "other tasks within the playbook. A displayLabel referencing a context key "
        "that is not consumed by any other task indicates the value has no functional "
        "purpose in the playbook flow."
    )
    error_message = (
        "Task '{0}' has a displayLabel that references the context key '{1}', "
        "but this key is not used in any other task in the playbook. "
        "displayLabel context keys should reference values that are consumed "
        "by other tasks in the playbook flow."
    )
    related_field = "displayLabel"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            for task_id, context_key in _get_invalid_display_label_keys(content_item):
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(task_id, context_key),
                        content_object=content_item,
                    )
                )
        return results


def _build_token_index(content_item: ContentTypes) -> Dict[str, Set[str]]:
    """Build an inverted index mapping each context-key token to the task IDs that contain it."""
    index: Dict[str, Set[str]] = defaultdict(set)
    for task_id, task_config in content_item.tasks.items():
        task_str = str(task_config.to_raw_dict)
        for token in _DOT_PATH_RE.findall(task_str):
            index[token].add(task_id)
        for key in _CONTEXT_KEY_RE.findall(task_str):
            index[key].add(task_id)
    return index


def _get_invalid_display_label_keys(
    content_item: ContentTypes,
) -> List[Tuple[str, str]]:
    """Return (task_id, context_key) pairs for displayLabel keys not used elsewhere."""
    pack_metadata = content_item.in_pack.pack_metadata_dict  # type: ignore[union-attr]
    if not pack_metadata:
        return []
    if not (
        pack_metadata.get("managed") is True
        and pack_metadata.get("source") == "autonomous"
    ):
        return []

    token_index = _build_token_index(content_item)

    invalid: List[Tuple[str, str]] = []
    for task_id, task_config in content_item.tasks.items():
        display_label = task_config.task.displayLabel
        if not display_label:
            continue
        for key in _CONTEXT_KEY_RE.findall(display_label):
            if not _key_used_elsewhere(key, task_id, token_index):
                invalid.append((task_id, key))
    return invalid


def _key_used_elsewhere(
    key: str, current_id: str, token_index: Dict[str, Set[str]]
) -> bool:
    """Check whether *key* or any of its dot-separated prefixes is used by another task.

    For ``A.B.C``, checks ``A.B.C``, then ``A.B``, then ``A``.
    This handles the complex root/accessor split where the split point is unknown.
    """
    parts = key.split(".")
    exclude = {current_id}
    for i in range(len(parts), 0, -1):
        prefix = ".".join(parts[:i])
        if token_index.get(prefix, set()) - exclude:
            return True
    return False
