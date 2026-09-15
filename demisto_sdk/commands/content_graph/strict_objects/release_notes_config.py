from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class StrictForceUpdate(BaseStrictModel):
    """Optional ``forceUpdate`` in ReleaseNotes/x_x_x.json: coupling-aware breaking-change notes (CIAC-17085 / CIAC-17086)."""

    breaking_changes_notes_loosely: Optional[str] = Field(
        None, alias="breakingChangesNotesLoosely"
    )
    breaking_changes_notes_tightly: Optional[str] = Field(
        None, alias="breakingChangesNotesTightly"
    )


class StrictReleaseNotesConfig(BaseStrictModel):
    breaking_changes: bool = Field(alias="breakingChanges")
    breaking_changes_notes: Optional[str] = Field(None, alias="breakingChangesNotes")
    marketplaces: Optional[List[MarketplaceVersions]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
    force_update: Optional[StrictForceUpdate] = Field(None, alias="forceUpdate")
