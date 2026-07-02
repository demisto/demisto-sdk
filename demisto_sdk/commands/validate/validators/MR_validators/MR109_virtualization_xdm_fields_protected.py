from __future__ import annotations

import re
from collections import Counter
from typing import Dict, Iterable, List, Tuple

from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ModelingRule

# Regex to extract xdm.<prefix>.user.<field> and xdm.<prefix>.identity.<field> from XIF content.
# Supports dotted sub-fields like xdm.source.user.first_name or xdm.target.identity.groups.
XDM_USER_IDENTITY_FIELD_PATTERN = re.compile(
    r"xdm\.(?:source|target|intermediate)\.(?:user|identity)\.[\w.]+"
)


def _get_mismatched_field_counts(
    xif_content: str,
) -> List[Tuple[str, int, str, int]]:
    """Parse XIF content and find user/identity fields with mismatched occurrence counts.

    For every ``xdm.<prefix>.user.<subfield>`` the number of occurrences must
    equal the number of occurrences of ``xdm.<prefix>.identity.<subfield>``,
    and vice-versa.

    Returns:
        A list of tuples (field, field_count, counterpart, counterpart_count)
        for each field whose occurrence count differs from its counterpart.
        Each pair is reported only once (the field that appears first alphabetically).
    """
    field_counts: Counter[str] = Counter(
        m.group(0) for m in XDM_USER_IDENTITY_FIELD_PATTERN.finditer(xif_content)
    )

    mismatched: List[Tuple[str, int, str, int]] = []
    seen: set[str] = set()

    for field in sorted(field_counts.keys()):
        if field in seen:
            continue

        if ".user." in field:
            counterpart = field.replace(".user.", ".identity.", 1)
        elif ".identity." in field:
            counterpart = field.replace(".identity.", ".user.", 1)
        else:
            continue

        field_count = field_counts[field]
        counterpart_count = field_counts.get(counterpart, 0)

        if field_count != counterpart_count:
            mismatched.append((field, field_count, counterpart, counterpart_count))
            seen.add(field)
            seen.add(counterpart)

    return mismatched


class VirtualizationXDMFieldsValidator(BaseValidator[ContentTypes]):
    error_code = "MR109"
    description = (
        "Validates that when a User or Identity XDM field is used in a modeling rule, "
        "the number of occurrences of each xdm.<prefix>.user.<subfield> must equal "
        "the number of occurrences of xdm.<prefix>.identity.<subfield>."
    )
    rationale = (
        "User and Identity XDM fields are correlated. For each "
        "xdm.<prefix>.user.<subfield> mapped in a modeling rule, the corresponding "
        "xdm.<prefix>.identity.<subfield> must appear the same number of times "
        "to ensure proper virtualization and data correlation across the platform."
    )
    error_message = (
        "The following XDM user/identity field pairs have mismatched  "
        "in the XIF file: {mismatched_fields}. "
        "For each xdm.{{prefix}}.user.{{subfield}}, the corresponding "
        "xdm.{{prefix}}.identity.{{subfield}} must appear."
    )
    related_field = "XIF"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.XIF]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            xif_content = content_item.xif_file.file_content
            if not xif_content:
                continue

            mismatched = _get_mismatched_field_counts(xif_content)
            if mismatched:
                details = ", ".join(
                    f'"{field}" appears {field_count} time(s) but '
                    f'"{counterpart}" appears {counterpart_count} time(s)'
                    for field, field_count, counterpart, counterpart_count in mismatched
                )
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            mismatched_fields=details
                        ),
                        content_object=content_item,
                    )
                )
        return results
