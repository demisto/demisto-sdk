from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Union, cast

from packaging.version import InvalidVersion, Version

from demisto_sdk.commands.common.constants import (
    PACKS_PACK_META_FILE_NAME,
    GitStatuses,
)
from demisto_sdk.commands.common.tools import (
    NoInternetConnectionException,
    find_pack_folder,
    get_file,
)
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.content_graph.objects.case_field import CaseField
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.knowledge import Knowledge
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[
    Integration,
    Script,
    Mapper,
    IncidentType,
    IncidentField,
    CaseField,
    AgentixAction,
    AgentixAgent,
    AgentixSkill,
    Knowledge,
]


class IsValidFromversionOnModifiedValidator(BaseValidator[ContentTypes]):
    error_code = "BC106"
    description = (
        "Check that the fromversion property was not changed on existing Content files."
    )
    rationale = "Changing the `fromversion` for a content item can break backward compatibility. For 'fromversion' info, see: https://xsoar.pan.dev/docs/integrations/yaml-file#version-and-tests"
    error_message = "Changing the minimal supported version field `fromversion` is not allowed. Please undo, or request a force merge."
    related_field = "fromversion"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if fromversion_modified(content_item)
        ]


FROMVERSION_KEYS = {"fromversion", "fromVersion"}


def fromversion_modified(content_item: ContentTypes) -> bool:
    if not content_item.old_base_content_object:
        return False
    old_file = cast(ContentTypes, content_item.old_base_content_object)
    if content_item.fromversion == old_file.fromversion:
        return False
    return not is_implicit_fromversion_made_explicit(content_item, old_file)


def is_implicit_fromversion_made_explicit(
    content_item: ContentTypes, old_file: ContentTypes
) -> bool:
    """True when the old file had no fromversion line and the new value does not exceed the old pack's serverMinVersion.

    The old item already could not install below the pack's serverMinVersion, so writing it explicitly changes nothing.
    """
    old_data = _read_at_sha(old_file.path, old_file.git_sha)
    if not old_data or FROMVERSION_KEYS & old_data.keys():
        return False
    try:
        pack_metadata_path = (
            find_pack_folder(Path(old_file.path)) / PACKS_PACK_META_FILE_NAME
        )
    except ValueError:
        return False
    server_min_version = _read_at_sha(pack_metadata_path, old_file.git_sha).get(
        "serverMinVersion"
    )
    if not server_min_version:
        return False
    try:
        return Version(content_item.fromversion) <= Version(server_min_version)
    except InvalidVersion:
        return False


def _read_at_sha(path: Path, git_sha: Optional[str]) -> dict:
    try:
        data = get_file(path, git_sha=git_sha)
    except (FileNotFoundError, NoInternetConnectionException, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
