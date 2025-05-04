from datetime import datetime
from typing import Any, Optional

from pydantic import DirectoryPath, Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import (
    JSON_Handler,
    XSOAR_Handler,
    YAML_Handler,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_file, write_dict
from demisto_sdk.commands.content_graph.common import (
    append_supported_modules,
    replace_marketplace_references,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import (
    MarketplaceSuffixPreparer,
)


class AgentixBase(ContentItem):
    is_enabled: bool = Field(..., alias="isEnabled")
    # pack_id: str = Field(..., alias="packID")
    # pack_name: str = Field(..., alias="packName")
    tags: Optional[list[str]]
    is_system: bool = Field(..., alias="isSystem")
    is_locked: bool = Field(..., alias="isLocked")
    is_detached: bool = Field(..., alias="isDetached")
    modified: Optional[datetime]
    modified_by: Optional[str] = Field(..., alias="modifiedBy")
    category: Optional[str] = Field(..., alias="category")
    version: str
    description: str
