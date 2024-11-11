from __future__ import annotations

from typing import Iterable, List

from packaging.version import parse

from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
    GitStatuses,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.objects.test_script import TestScript
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
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
    pack_ids_to_added_rn: dict[str, str] = {}
    checked_packs: set[str] = set()

    def should_skip_check(self, content_item: ContentItem) -> bool:
        if isinstance(content_item, (TestPlaybook, TestScript)):
            return True
        if isinstance(content_item, Integration):
            old_content = content_item.old_base_content_object
            assert isinstance(old_content, Integration)
            return (
                not content_item.git_status
                and not old_content.description_file.git_status
            )
        if isinstance(content_item, ModelingRule):
            old_content = content_item.old_base_content_object
            assert isinstance(old_content, ModelingRule)
            return (
                not content_item.git_status
                and not old_content.xif_file.git_status
                and not old_content.schema_file.git_status
            )
        if content_item.git_status == GitStatuses.RENAMED:
            return not IsMissingReleaseNotes.is_pack_move(content_item)
        return content_item.git_status is None

    @staticmethod
    def is_pack_move(content_item: ContentItem) -> bool:
        old_content = content_item.old_base_content_object
        assert isinstance(old_content, ContentItem)
        return content_item.pack_id != old_content.pack_id

    def get_api_module_imports(self, content_item: ContentItem) -> list[ContentItem]:
        try:
            api_module_node: Script = self.graph.search(
                object_id=content_item.object_id
            )[0]
        except IndexError:
            logger.warning(f"Could not find {API_MODULES_PACK} in graph")
            return []
        return [c for c in api_module_node.imported_by]

    def get_missing_rns_for_api_module_dependents(
        self, content_item: ContentItem
    ) -> list[ValidationResult]:
        dependent_items = self.get_api_module_imports(content_item)
        results = [
            ValidationResult(
                validator=self,
                message=self.error_message.format(API_MODULES_PACK),
                content_object=c.in_pack,
            )
            for c in dependent_items
            if c.in_pack
            and self.is_missing_rn(c)
            and c.pack_id not in self.checked_packs
        ]
        self.checked_packs.update([c.pack_id for c in dependent_items])
        return results

    def is_missing_rn(self, content_item: ContentItem) -> bool:
        pack = content_item.in_pack
        assert pack and pack.pack_version
        return (
            pack.pack_version > parse("1.0.0")
            and pack.object_id not in self.pack_ids_to_added_rn
        )

    def get_pack_ids_to_added_rn(self, packs: list[Pack]) -> dict:
        return {
            p.object_id: p.release_note.file_content
            for p in packs
            if isinstance(p.old_base_content_object, Pack)
            and p.old_base_content_object.release_note.git_status == GitStatuses.ADDED
        }

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: list[ValidationResult] = []
        self.pack_ids_to_added_rn = self.get_pack_ids_to_added_rn(
            [p for p in content_items if isinstance(p, Pack)]
        )
        for content_item in content_items:
            if isinstance(content_item, ContentItem):
                if (
                    self.should_skip_check(content_item)
                    or content_item.pack_id in self.checked_packs
                ):
                    logger.debug(f"Skipping RN106 for {content_item.path}")
                    continue
                logger.debug(f"Running RN106 for {content_item.path}")
                assert content_item.in_pack
                if content_item.in_pack.name == API_MODULES_PACK:
                    results.extend(
                        self.get_missing_rns_for_api_module_dependents(content_item)
                    )
                elif self.is_missing_rn(content_item):
                    self.checked_packs.add(content_item.pack_id)
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(content_item.pack_id),
                            content_object=content_item.pack,
                        )
                    )
        return results
