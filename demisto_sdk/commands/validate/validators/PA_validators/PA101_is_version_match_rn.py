from __future__ import annotations

from typing import Iterable, List

from packaging.version import Version

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsVersionMatchRnValidator(BaseValidator[ContentTypes]):
    error_code = "PA101"
    description = "Validate that the version mentioned in the Pack metadata matches the latest RN version."
    rationale = (
        "Clear documentation for each version change helps users know what's new."
        "For more information, see https://xsoar.pan.dev/docs/packs/packs-format#content-packs-versioning"
    )
    error_message = "The currentVersion in the metadata ({0}) doesn't match the latest rn version ({1})."
    related_field = "currentVersion"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.current_version,
                    (content_item.latest_rn_version or "none"),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.current_version != "1.0.0"
                and not content_item.latest_rn_version
            )
            or content_item.latest_rn_version
            and Version(content_item.current_version)  # type:ignore[arg-type]
            != Version(content_item.latest_rn_version)
        ]
