from __future__ import annotations

import typing
from typing import Iterable, Union

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    IGNORED_PACK_NAMES,
    PACK_METADATA_REQUIRE_RN_FIELDS,
    SKIP_RELEASE_NOTES_FOR_TYPES,
    GitStatuses,
)
from demisto_sdk.commands.common.tools import find_type
from demisto_sdk.commands.content_graph.objects import (
    AssetsModelingRule,
    BasePlaybook,
    BaseScript,
    CaseField,
    CaseLayout,
    CaseLayoutRule,
    Classifier,
    CorrelationRule,
    Dashboard,
    GenericDefinition,
    GenericField,
    GenericModule,
    GenericType,
    IncidentField,
    IncidentType,
    IndicatorField,
    IndicatorType,
    Integration,
    Job,
    Layout,
    LayoutRule,
    List,
    Mapper,
    ModelingRule,
    ParsingRule,
    Playbook,
    PreProcessRule,
    Report,
    Script,
    Trigger,
    Widget,
    Wizard,
    XDRCTemplate,
    XSIAMDashboard,
    XSIAMReport,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.tools import is_new_pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[
    Pack,
    Integration,
    Script,
    Playbook,
    AssetsModelingRule,
    BasePlaybook,
    BaseScript,
    CaseField,
    CaseLayout,
    CaseLayoutRule,
    Classifier,
    CorrelationRule,
    Dashboard,
    GenericDefinition,
    GenericField,
    GenericModule,
    GenericType,
    IncidentField,
    IncidentType,
    IndicatorField,
    IndicatorType,
    Job,
    Layout,
    LayoutRule,
    Mapper,
    ModelingRule,
    Pack,
    ParsingRule,
    Playbook,
    PreProcessRule,
    Report,
    Script,
    Trigger,
    Widget,
    Wizard,
    XDRCTemplate,
    XSIAMDashboard,
    XSIAMReport,
    List,
]


class PackMetadataVersionShouldBeRaisedValidator(BaseValidator[ContentTypes]):
    error_code = "PA114"
    description = "Ensure that the pack metadata version is raised on relevant changes."
    rationale = (
        "When updating a pack, its version needs to be raised to maintain traceability."
    )
    error_message = (
        "The pack version (currently: {old_version}) needs to be raised - "
        "make sure you are merged from master and "
        "update release notes by running:\n"
        "`demisto-sdk update-release-notes -g` - for automatically generation of release notes and version\n"
        "`demisto-sdk update-release-notes -i Packs/{pack} -u "
        "(major|minor|revision|documentation)` for a specific pack and version."
    )

    @staticmethod
    def should_bump(content_item: ContentTypes):
        """Return if the version should be bumped as a result of the input content item.
        Args:
            content_item (ContentTypes): The content item for which to decide.

        Return:
            (Boolean) True if should bump due to change False otherwise.
        """
        if content_item.pack_name in IGNORED_PACK_NAMES:
            return False

        if isinstance(content_item, ContentItem) and is_new_pack(content_item.pack):
            return False

        if content_item.git_status is None and content_item.content_type.value in [
            Integration.content_type.value,
            Script.content_type.value,
        ]:
            # If the file collected is an Integration or Script and they were not modified directly,
            # check that their code files and description files were not modified as well.
            related_files_unchanged = [
                content_item.code_file.git_status is None,  # type: ignore[union-attr]
            ]
            if content_item.content_type.value == Integration.content_type.value:
                related_files_unchanged.append(
                    content_item.description_file.git_status is None  # type: ignore[union-attr]
                )

            return not all(related_files_unchanged)

        if isinstance(content_item, Pack):
            if is_new_pack(content_item):
                return False
            # If it's a pack content type check for the fields that require RNs.
            old_dict = content_item.old_base_content_object.to_dict()  # type: ignore[union-attr]
            current_dict = content_item.to_dict()  # type: ignore[union-attr]
            for field in PACK_METADATA_REQUIRE_RN_FIELDS:
                if old_dict.get(field) != current_dict.get(field):
                    return True

        elif content_item.git_status is not None:
            # If the content_item was changed
            if find_type(str(content_item.path)) in SKIP_RELEASE_NOTES_FOR_TYPES:  # type: ignore[union-attr]
                # If we should skip the release notes
                return False
            return True

        return False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> typing.List[ValidationResult]:
        validation_results = []
        content_packs = {}
        content_packs_ids_to_bump = set()
        # Go over all the content items
        for content_item in content_items:
            is_metadata_item = (
                content_item.content_type.value == Pack.content_type.value
            )
            if is_metadata_item:
                # Collect content metadata items and link them to their pack ids.
                content_packs[content_item.pack_id] = content_item  # type: ignore[union-attr]

            if content_item.pack_id not in content_packs_ids_to_bump:
                should_bump = self.should_bump(content_item)
                if should_bump:
                    # Collect content pack ids that should be bumped.
                    content_packs_ids_to_bump.add(content_item.pack_id)  # type: ignore[union-attr]

        # Go over all the pack ids that need to be bumped.
        for pack_id in content_packs_ids_to_bump:
            # Access them via the dict that was created earlier
            pack = content_packs[pack_id]
            # Check if their old version >= current version
            old_version = pack.old_base_content_object.current_version  # type: ignore[union-attr]
            current_version = pack.current_version  # type: ignore[union-attr]
            if (
                current_version
                and Version(old_version) >= Version(current_version)
                and not pack.git_status == GitStatuses.ADDED
            ):
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            old_version=old_version,
                            pack=pack.name,  # type: ignore[union-attr]
                        ),
                        content_object=pack,
                    )
                )
        return validation_results
