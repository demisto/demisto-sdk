from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
    GitStatuses,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.tools import extract_rn_headers
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN106_missing_release_notes_for_pack import (
    IsMissingReleaseNotes,
)

ContentTypes = BaseContent


class IsMissingReleaseNoteEntries(BaseValidator[ContentTypes]):
    error_code = "RN107"
    description = "Validate that there are no missing release notes entries."
    rationale = "Ensure that whenever there is an actual pack update, it is visible to customers."
    error_message = (
        'No release note entry was found for the {file_type.value.lower()} "{entity_name}" in the '
        "{pack_name} pack. Please rerun the update-release-notes command without -u to "
        "generate an updated template. If you are trying to exclude an item from the release "
        "notes, please refer to the documentation found here - "
        "https://xsoar.pan.dev/docs/integrations/changelog#excluding-items"
    )
    related_field = "release notes"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.RELEASE_NOTE]
    content_items_with_added_rn: list[Path] = []

    @staticmethod
    def should_skip_check(
        content_item: ContentItem, packs_with_added_rn: list[str]
    ) -> bool:
        if content_item.pack_id == API_MODULES_PACK:
            return False
        return (
            content_item.pack_id not in packs_with_added_rn
            or IsMissingReleaseNotes.should_skip_check(content_item)
        )

    def get_missing_rns_for_api_module_dependents(
        self, api_module: ContentItem
    ) -> dict[Path, ValidationResult]:
        dependent_items = self.graph.get_api_module_imports(api_module.object_id)
        result = {
            c.path: ValidationResult(
                validator=self,
                message=self.error_message.format(
                    entity_name=c.object_id, pack_name=c.pack_id
                ),
                content_object=c,
            )
            for c in dependent_items
            if c.object_id not in self.content_items_with_added_rn
        }
        return result

    @staticmethod
    def get_content_items_with_added_rns(
        content_items: Iterable[BaseContent],
    ) -> list[Path]:
        pack_to_rn_headers = {
            p.object_id: extract_rn_headers(p.release_note.file_content)
            for p in content_items
            if isinstance(p, Pack) and p.release_note.git_status == GitStatuses.ADDED
        }
        return [
            c.path
            for c in content_items
            if isinstance(c, ContentItem)
            and c.pack_id in pack_to_rn_headers
            and c.display_name
            in pack_to_rn_headers[c.pack_id].get(c.content_type.as_folder, [])
        ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: dict[Path, ValidationResult] = {}
        api_module_results: dict[Path, ValidationResult] = {}

        packs_with_added_rn = IsMissingReleaseNotes.get_packs_with_added_rns(
            content_items
        )
        self.content_items_with_added_rn = self.get_content_items_with_added_rns(
            content_items
        )

        for content_item in content_items:
            if isinstance(content_item, ContentItem):
                if self.should_skip_check(content_item, packs_with_added_rn):
                    logger.debug(f"Skipping RN107 for {content_item.path}")
                    continue

                logger.debug(f"Running RN107 for {content_item.path}")

                if content_item.pack_id == API_MODULES_PACK:
                    api_module_results.update(
                        self.get_missing_rns_for_api_module_dependents(content_item)
                    )

                elif content_item.path not in self.content_items_with_added_rn:
                    results[content_item.path] = ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            entity_name=content_item.object_id,
                            pack_name=content_item.pack_id,
                        ),
                        content_object=content_item.pack,
                    )

        return list((results | api_module_results).values())
