from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.tools import (
    extract_rn_headers,
    should_skip_rn_check,
    was_rn_added,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = BaseContent


class IsMissingReleaseNoteEntries(BaseValidator[ContentTypes]):
    error_code = "RN107"
    description = "Validate that there are no missing release notes entries."
    rationale = "Ensure that whenever there is an actual pack update, it is visible to customers."
    error_message = (
        'No release note entry was found for the {file_type} "{entity_name}" in the '
        "{pack_name} pack. Please rerun the update-release-notes command without -u to "
        "generate an updated template. If you are trying to exclude an item from the release "
        "notes, please refer to the documentation found here - "
        "https://xsoar.pan.dev/docs/integrations/changelog#excluding-items"
    )
    related_field = "release notes"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.RELEASE_NOTE]
    pack_to_rn_headers: dict[str, dict[str, list]] = {}

    def should_skip_check(self, content_item: ContentItem) -> bool:
        if content_item.pack_id == API_MODULES_PACK:
            return False
        return (
            content_item.pack_id not in self.pack_to_rn_headers
            or should_skip_rn_check(content_item)
        )

    def get_missing_rns_for_api_module_dependents(
        self, api_module: ContentItem
    ) -> dict[Path, ValidationResult]:
        dependent_items = self.graph.get_api_module_imports(api_module.object_id)
        logger.debug(
            f"Validating {api_module.object_id} dependents: {[d.object_id for d in dependent_items]}"
        )
        result = {
            c.path: ValidationResult(
                validator=self,
                message=self.error_message.format(
                    file_type=c.content_type.value.lower(),
                    entity_name=c.display_name,
                    pack_name=c.pack_id,
                ),
                content_object=c,
                path=c.pack.release_note.file_path,
            )
            for c in dependent_items
            if c.pack_id in self.pack_to_rn_headers and self.is_missing_rn(c)
        }
        return result

    @staticmethod
    def get_pack_to_rn_headers(
        content_items: Iterable[BaseContent],
    ) -> dict[str, dict[str, list]]:
        pack_to_rn_headers = {
            p.object_id: extract_rn_headers(
                p.release_note.file_content, remove_prefixes=True
            )
            for p in content_items
            if isinstance(p, Pack) and was_rn_added(p)
        }
        return pack_to_rn_headers

    def is_missing_rn(self, c: ContentItem) -> bool:
        return c.display_name not in self.pack_to_rn_headers[c.pack_id].get(
            c.content_type.as_rn_header, []
        )

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: dict[Path, ValidationResult] = {}
        api_module_results: dict[Path, ValidationResult] = {}

        self.pack_to_rn_headers = self.get_pack_to_rn_headers(content_items)

        for content_item in content_items:
            if isinstance(content_item, ContentItem):
                if self.should_skip_check(content_item):
                    logger.debug(f"Skipping RN107 for {content_item.path}")
                    continue

                logger.debug(f"Running RN107 for {content_item.path}")

                if content_item.pack_id == API_MODULES_PACK:
                    api_module_results.update(
                        self.get_missing_rns_for_api_module_dependents(content_item)
                    )

                elif self.is_missing_rn(content_item):
                    results[content_item.path] = ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            file_type=content_item.content_type.value.lower(),
                            entity_name=content_item.display_name,
                            pack_name=content_item.pack_id,
                        ),
                        content_object=content_item,
                        path=content_item.pack.release_note.file_path,
                    )

        return list((results | api_module_results).values())
