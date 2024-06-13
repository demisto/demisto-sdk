from __future__ import annotations

from typing import Iterable, List

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    PACKS_PACK_META_FILE_NAME,
)
from demisto_sdk.commands.common.tools import get_remote_file
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
    is_auto_fixable = False
    # Validate manager should populate the external args for the validation.
    external_args = {"prev_ver": None}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        validation_results = []
        prev_ver_tag = self.external_args.get("prev_ver", DEMISTO_GIT_PRIMARY_BRANCH)
        for content_item in content_items:
            old_meta_file_content = get_remote_file(
                str(content_item.path / PACKS_PACK_META_FILE_NAME), tag=prev_ver_tag
            )
            old_version = old_meta_file_content.get("currentVersion", "0.0.0")
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
