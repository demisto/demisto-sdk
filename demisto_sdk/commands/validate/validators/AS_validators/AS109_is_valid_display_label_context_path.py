from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, Iterable, List, Set, Tuple, Union

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.tools import is_autonomous_pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Playbook]

# Extracts context keys from ${...} placeholders, e.g. ${issue.id} -> "issue.id"
_CONTEXT_KEY_RE = re.compile(r"\$\{([^}]+)\}")

# Extracts the leading identifier from a context path, ignoring DT filters
# and dot suffixes.  Applied to values captured by _CONTEXT_KEY_RE, 'root'
# fields, and 'simple' fields in the stringified task dict.
_ROOT_RE = re.compile(r"^([A-Za-z_]\w*)")

# Matches 'root' and 'simple' string values in the Python repr of a task dict.
# Captures the value portion so we can extract its leading identifier.
# E.g.  "'root': 'File'"  → captures "File"
#        "'simple': 'SuspiciousCommandLines'"  → captures "SuspiciousCommandLines"
_FIELD_VAL_RE = re.compile(r"'(?:root|simple)':\s*'([^']+)'")


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


def _get_root_name(path: str) -> str:
    """Extract the leading identifier (root name) from a context path.

    Strips DT filter expressions and dot suffixes.
    ``FileEnrichment(val.TIMScore == 0).Value`` → ``FileEnrichment``
    ``File.SHA256`` → ``File``
    """
    m = _ROOT_RE.match(path)
    return m.group(1) if m else path


def _extract_roots_from_task(task_str: str) -> Set[str]:
    """Extract all context-key root names from the string repr of a task dict.

    Scans for ``${...}`` references and ``'root'``/``'simple'`` field values.
    """
    roots: Set[str] = set()
    for key in _CONTEXT_KEY_RE.findall(task_str):
        roots.add(_get_root_name(key))
    for val in _FIELD_VAL_RE.findall(task_str):
        roots.add(_get_root_name(val))
    return roots


def _get_invalid_display_label_keys(
    content_item: ContentTypes,
) -> List[Tuple[str, str]]:
    """Return (task_id, context_key) pairs for displayLabel keys not used elsewhere."""
    if not is_autonomous_pack(content_item.in_pack):
        return []

    # Build inverted index: root name → set of task IDs that reference it
    root_index: Dict[str, Set[str]] = defaultdict(set)
    for task_id, task_config in content_item.tasks.items():
        for root in _extract_roots_from_task(str(task_config.to_raw_dict)):
            root_index[root].add(task_id)

    invalid: List[Tuple[str, str]] = []
    for task_id, task_config in content_item.tasks.items():
        display_label = task_config.task.displayLabel
        if not display_label:
            continue
        for key in _CONTEXT_KEY_RE.findall(display_label):
            root = _get_root_name(key)
            if not (root_index.get(root, set()) - {task_id}):
                invalid.append((task_id, key))
    return invalid
