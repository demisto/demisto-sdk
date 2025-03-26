from __future__ import annotations

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
    is_new_pack,
    should_skip_rn_check,
    was_rn_added,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = BaseContent


class IsMissingReleaseNotes(BaseValidator[ContentTypes]):
    error_code = "RN106"
    description = "Validate that there are no missing release notes."
    rationale = "Ensure that whenever there is an actual pack update, it is visible to customers."
    error_message = (
        "Release notes were not found. Please run `demisto-sdk "
        "update-release-notes -i Packs/{0} -u (major|minor|revision|documentation)` to "
        "generate release notes according to the new standard. You can refer to the documentation "
        "found here: https://xsoar.pan.dev/docs/integrations/changelog for more information."
    )
    related_field = "release notes"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.RELEASE_NOTE]
    valid_packs: list[str] = []
    checked_packs: set[str] = set()
    run_on_deprecated = True

    def get_missing_rns_for_api_module_dependents(
        self, api_module: ContentItem
    ) -> dict[str, ValidationResult]:
        dependent_items = self.graph.get_api_module_imports(api_module.object_id)
        result = {
            c.pack_id: ValidationResult(
                validator=self,
                message=self.error_message.format(API_MODULES_PACK),
                content_object=c.pack,
            )
            for c in dependent_items
            if c.pack_id not in self.valid_packs
        }
        return result

    @staticmethod
    def get_valid_packs(content_objects: Iterable[BaseContent]) -> list[str]:
        return [
            p.object_id
            for p in content_objects
            if isinstance(p, Pack) and (was_rn_added(p) or is_new_pack(p))
        ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: dict[str, ValidationResult] = {}
        api_module_results: dict[str, ValidationResult] = {}

        self.valid_packs = self.get_valid_packs(content_items)

        for content_item in content_items:
            if isinstance(content_item, ContentItem):
                if (
                    should_skip_rn_check(content_item)
                    or content_item.pack_id in self.checked_packs
                ):
                    logger.debug(f"Skipping RN106 for {content_item.path}")
                    continue

                logger.debug(f"Running RN106 for {content_item.path}")

                if content_item.pack_id == API_MODULES_PACK:
                    api_module_results.update(
                        self.get_missing_rns_for_api_module_dependents(content_item)
                    )
                    self.checked_packs.update(api_module_results.keys())

                elif content_item.pack_id not in self.valid_packs:
                    results[content_item.pack_id] = ValidationResult(
                        validator=self,
                        message=self.error_message.format(content_item.pack_id),
                        content_object=content_item.pack,
                    )
                    self.checked_packs.add(content_item.pack_id)

        return list((results | api_module_results).values())
