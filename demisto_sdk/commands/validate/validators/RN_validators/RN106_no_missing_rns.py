from __future__ import annotations

from typing import Iterable, List

from packaging.version import parse

from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
    GitStatuses,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.objects.test_script import TestScript
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ContentItem


class IsMissingReleaseNotes(BaseValidator[ContentTypes]):
    error_code = "RN106"
    description = "Validate that there are no missing release notes."
    rationale = "Ensure that whenever there is an actual pack update, it is visible to customers."
    error_message = (
        f"Release notes were not found. Please run `demisto-sdk "
        f"update-release-notes -i Packs/{0} -u (major|minor|revision|documentation)` to "
        f"generate release notes according to the new standard. You can refer to the documentation "
        f"found here: https://xsoar.pan.dev/docs/integrations/changelog for more information."
    )
    related_field = "release notes"
    is_auto_fixable = False
    expected_git_statuses = [
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
        GitStatuses.DELETED,
    ]
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    @staticmethod
    def is_pack_missing_rns(pack: Pack) -> bool:
        return bool(
            pack.pack_version
            and pack.pack_version > parse("1.0.0")
            and pack.release_note.git_status != GitStatuses.ADDED
        )

    def get_missing_rns_for_api_module_dependents(
        self, api_module: Script
    ) -> dict[str, Pack]:
        dependent_packs: list[Pack] = [
            dependency.in_pack
            for dependency in api_module.imported_by
            if dependency.in_pack
        ]
        return {
            pack.object_id: pack
            for pack in dependent_packs
            if self.is_pack_missing_rns(pack)
        }

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: dict[str, Pack] = {}
        for content_item in content_items:
            logger.info(f"{content_item.path=}")
            if isinstance(content_item, (TestPlaybook, TestScript)):
                continue
            if (
                isinstance(content_item, Script)
                and content_item.in_pack
                and content_item.in_pack.name == API_MODULES_PACK
            ):
                results.update(
                    self.get_missing_rns_for_api_module_dependents(content_item)
                )
            elif content_item.in_pack and self.is_pack_missing_rns(
                content_item.in_pack
            ):
                results[content_item.pack_id] = content_item.in_pack
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(pack_id),
                content_object=pack,
            )
            for pack_id, pack in results.items()
        ]
