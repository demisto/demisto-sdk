from __future__ import annotations

from typing import Iterable, List

from packaging.version import parse

from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
    GitStatuses,
)
from demisto_sdk.commands.common.logger import logger
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

ContentTypes = ContentItem


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

    @staticmethod
    def should_skip_check(content_item: ContentItem) -> bool:
        if isinstance(content_item, (TestPlaybook, TestScript)):
            return True
        if isinstance(content_item, Integration):
            if (
                not content_item.git_status
                and not content_item.description_file.git_status
            ):
                return True
        if isinstance(content_item, ModelingRule):
            if not (
                content_item.git_status
                or content_item.xif_file.git_status
                or content_item.schema_file.git_status
            ):
                return True
        if content_item.git_status == GitStatuses.RENAMED:
            return True  # todo
        return False

    @staticmethod
    def is_api_module(content_item: ContentItem) -> bool:
        return (
            isinstance(content_item, Script)
            and content_item.in_pack is not None
            and content_item.in_pack.name == API_MODULES_PACK
        )

    def get_missing_rns_for_api_module_dependents(
        self, api_module: ContentItem
    ) -> dict[str, Pack]:
        try:
            api_module_node: Script = self.graph.search(path=api_module.path)[0]
        except IndexError:
            raise Exception(
                f"Unexpected: could not find {api_module.object_id} in graph"
            )
        dependent_packs: list[Pack] = [
            dependency.in_pack
            for dependency in api_module_node.imported_by
            if dependency.in_pack
        ]
        logger.info(f"api module: {[p.object_id for p in dependent_packs]}")
        return {
            pack.object_id: pack
            for pack in dependent_packs
            if self.is_pack_missing_rns(pack)
        }

    @staticmethod
    def is_pack_missing_rns(pack: Pack) -> bool:
        is_pack_update = pack.pack_version is not None and pack.pack_version > parse(
            "1.0.0"
        )
        # why GitStatus of splunkpy release note is not "ADDED", but None?
        no_new_release_note = pack.release_note.git_status != GitStatuses.ADDED
        logger.info(f"{pack.object_id} = {pack.pack_version}")
        logger.info(
            f"{pack.release_note.latest_rn_version} = {pack.release_note.git_status}"
        )
        return is_pack_update and no_new_release_note

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: dict[str, Pack] = {}
        for content_item in content_items:
            logger.info(f"{content_item.path=}")
            if self.should_skip_check(content_item):
                logger.info("skipping check")
                continue
            if self.is_api_module(content_item):
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
