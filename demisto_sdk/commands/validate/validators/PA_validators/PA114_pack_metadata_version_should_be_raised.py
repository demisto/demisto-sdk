from __future__ import annotations

from typing import Iterable, List

from packaging.version import Version

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class PackMetadataVersionShouldBeRaisedValidator(BaseValidator[ContentTypes]):
    error_code = "PA114"
    description = "Ensure that the pack metadata is raised on relevant changes."
    rationale = (
        "When updating a pack, its version needs to be raised to maintain traceability."
    )
    error_message = (
        "The pack version (currently: {old_version}) needs to be raised - "
        "make sure you are merged from master and "
        'update the "currentVersion" field in the '
        "pack_metadata.json or in case release notes are required run:\n"
        "`demisto-sdk update-release-notes -i Packs/{pack} -u "
        "(major|minor|revision|documentation)` to "
        "generate them according to the new standard."
    )
    related_field = "currentVersion, name"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        validation_results = []
        for content_item in content_items:
            old_version = content_item.old_base_content_object.current_version  # type: ignore[union-attr]
            if content_item.current_version and Version(old_version) >= Version(
                content_item.current_version
            ):
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            old_version=old_version, pack=content_item.name
                        ),
                        content_object=content_item,
                    )
                )
        return validation_results
