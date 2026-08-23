from typing import List, Optional, Union

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class StrictBreakingChangesNotesTightly(BaseStrictModel):
    """
    Coupling-aware breaking-change notes for Tightly Coupled content items, nested under
    `forceUpdate.breakingChangesNotesTightly` in a per-version breaking-changes config file
    (ReleaseNotes/x_x_x.json). Consumed by the Managed Content upload to build the changelog.json
    release notice. See CIAC-17086.
    """

    message: Optional[str] = None
    more_info: Optional[str] = None


class StrictForceUpdate(BaseStrictModel):
    """
    The optional `forceUpdate` object in a per-version breaking-changes config file
    (ReleaseNotes/x_x_x.json). Holds coupling-aware breaking-change notes used by the ConnectUS
    (Managed Content) flow. Omitting it preserves full backward compatibility. See CIAC-17085 / CIAC-17086.

    - `breakingChangesNotesLoosely`: Breaking-change notes for Loosely Coupled items only.
    - `breakingChangesNotesTightly`: Breaking-change notes for Tightly Coupled items only
      (either a plain string or a {message, more_info} object).
    """

    breaking_changes_notes_loosely: Optional[str] = Field(
        None, alias="breakingChangesNotesLoosely"
    )
    breaking_changes_notes_tightly: Optional[
        Union[str, StrictBreakingChangesNotesTightly]
    ] = Field(None, alias="breakingChangesNotesTightly")


class StrictReleaseNotesConfig(BaseStrictModel):
    breaking_changes: bool = Field(alias="breakingChanges")
    breaking_changes_notes: Optional[str] = Field(None, alias="breakingChangesNotes")
    marketplaces: Optional[List[MarketplaceVersions]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
    force_update: Optional[StrictForceUpdate] = Field(None, alias="forceUpdate")
