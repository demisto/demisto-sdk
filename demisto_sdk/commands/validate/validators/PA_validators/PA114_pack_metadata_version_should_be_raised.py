from __future__ import annotations

import typing
from typing import Iterable, Union

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    PACK_METADATA_REQUIRE_RN_FIELDS,
    SKIP_RELEASE_NOTES_FOR_TYPES,
    FileType,
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
from demisto_sdk.commands.content_graph.objects.pack import Pack
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

    @staticmethod
    def should_bump_is_metadata(content_item: ContentTypes):
        """Return if the version should be bumped as a result of the input content item.
        Args:
            content_item (ContentTypes): The content item for which to decide.

        Return:
            ((Boolean) True if should bump due to change False otherwise,
             (Boolean) True if the content item is the pack_metadata False otherwise)
        """
        content_item_type = find_type(str(content_item.path))  # type: ignore[union-attr]
        is_metadata = False

        if (
            not content_item_type
            and content_item.content_type.value == Pack.content_type.value  # type: ignore[union-attr]
        ):
            content_item_type = FileType.METADATA
            is_metadata = True

        if content_item_type not in SKIP_RELEASE_NOTES_FOR_TYPES:
            if content_item_type != FileType.METADATA:
                return True, False
            else:
                is_metadata = True
                old_dict = content_item.old_base_content_object.to_dict()  # type: ignore[union-attr]
                current_dict = content_item.to_dict()  # type: ignore[union-attr]
                for field in PACK_METADATA_REQUIRE_RN_FIELDS:
                    if old_dict.get(field) != current_dict.get(field):
                        return True, True
        return False, is_metadata

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> typing.List[ValidationResult]:
        validation_results = []
        content_packs = {}
        content_packs_ids_to_bump = []
        # Go over all the content items
        for content_item in content_items:
            should_bump, is_metadata = self.should_bump_is_metadata(content_item)
            if should_bump:
                pack_id = content_item.pack_id  # type: ignore[union-attr]
                if pack_id not in content_packs_ids_to_bump:
                    # Collect content pack ids that should be bumped.
                    content_packs_ids_to_bump.append(pack_id)
            if is_metadata:
                # Collect content metadata items and link them to their pack ids.
                content_packs[content_item.pack_id] = content_item  # type: ignore[union-attr]

        # Go over all the pack ids that need to be bumped.
        for pack_id in content_packs_ids_to_bump:
            # Access them via the dict that was created earlier
            pack = content_packs[pack_id]
            # Check if their old version >= current version
            old_version = pack.old_base_content_object.current_version  # type: ignore[union-attr]
            current_version = pack.current_version  # type: ignore[union-attr]
            if current_version and Version(old_version) >= Version(current_version):
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
