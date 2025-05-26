from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class StrictReleaseNotesConfig(BaseStrictModel):
    breaking_changes: bool = Field(alias="breakingChanges")
    breaking_changes_notes: Optional[str] = Field(None, alias="breakingChangesNotes")
    marketplaces: Optional[List[MarketplaceVersions]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
