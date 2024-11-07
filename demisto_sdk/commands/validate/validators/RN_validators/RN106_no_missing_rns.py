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
    pack_id_to_rn: dict[str, str] = {}

    @staticmethod
    def should_skip_check(content_item: ContentItem) -> bool:
        if isinstance(content_item, (TestPlaybook, TestScript)):
            return True
        if isinstance(content_item, Integration):
            assert isinstance(content_item.old_base_content_object, Integration)
            return (
                not content_item.git_status
                and not content_item.old_base_content_object.description_file.git_status
            )
        if isinstance(content_item, ModelingRule):
            assert isinstance(content_item.old_base_content_object, ModelingRule)
            return (
                not content_item.git_status
                and not content_item.old_base_content_object.xif_file.git_status
                and not content_item.old_base_content_object.schema_file.git_status
            )
        if content_item.git_status == GitStatuses.RENAMED:
            return not IsMissingReleaseNotes.is_pack_move(content_item)
        return content_item.git_status is None

    @staticmethod
    def is_pack_move(content_item: ContentItem) -> bool:
        current_pack = content_item.in_pack
        prev_ver = content_item.old_base_content_object
        assert isinstance(prev_ver, ContentItem) and prev_ver.in_pack
        return (
            current_pack is not None
            and current_pack.object_id != prev_ver.in_pack.object_id
        )

    def get_missing_rns_for_api_module_dependents(
        self, api_module: ContentItem
    ) -> dict[str, Pack]:
        try:
            api_module_node: Script = self.graph.search(object_id=api_module.object_id)[
                0
            ]
        except IndexError:
            logger.warning(f"Could not find {api_module.object_id} in graph")
            return {}
        dependent_items = [c for c in api_module_node.imported_by]
        return {
            c.in_pack.object_id: c.in_pack
            for c in dependent_items
            if c.in_pack and self.is_missing_rn(c)
        }

    def is_missing_rn(self, content_item: ContentItem) -> bool:
        pack = content_item.in_pack
        assert pack and pack.pack_version
        return (
            pack.pack_version > parse("1.0.0")
            and pack.object_id not in self.pack_id_to_rn
        )

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: dict[str, Pack] = {}
        self.pack_id_to_rn = {
            p.object_id: p.release_note.file_content
            for p in content_items
            if isinstance(p, Pack)
            and isinstance(p.old_base_content_object, Pack)
            and p.old_base_content_object.release_note.git_status == GitStatuses.ADDED
        }
        for content_item in content_items:
            if isinstance(content_item, ContentItem):
                logger.info(f"{content_item.path=}")
                if self.should_skip_check(content_item):
                    logger.info("skipping check")
                    continue
                assert content_item.in_pack
                if content_item.in_pack.name == API_MODULES_PACK:
                    results.update(
                        self.get_missing_rns_for_api_module_dependents(content_item)
                    )
                elif self.is_missing_rn(content_item):
                    results[content_item.pack_id] = content_item.pack
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(pack_id),
                content_object=pack,
            )
            for pack_id, pack in results.items()
        ]
