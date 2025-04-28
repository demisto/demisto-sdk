from datetime import datetime
from typing import Optional, Any

from pydantic import Field, DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import write_dict, get_file
from demisto_sdk.commands.content_graph.common import replace_marketplace_references, append_supported_modules
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import MarketplaceSuffixPreparer

from demisto_sdk.commands.common.handlers import (
    JSON_Handler,
    XSOAR_Handler,
    YAML_Handler,
)


class AgentixBase(ContentItem):
    is_enabled: bool = Field(..., alias="isEnabled")
    pack_id1: str = Field(..., alias="packID")
    pack_name1: str = Field(..., alias="packName")
    tags: Optional[list[str]]
    is_system: bool = Field(..., alias="isSystem")
    is_locked: bool = Field(..., alias="isLocked")
    is_detached: bool = Field(..., alias="isDetached")
    modified: Optional[datetime]
    modified_by: Optional[str] = Field(..., alias="modifiedBy")
    category: Optional[str] = Field(..., alias="modifiedBy")
    _id: str = Field(..., alias="id")
    version: str
    display_name: str = Field(..., alias="name")
    description: str
    pack: Any = Field(None, exclude=True, repr=False)
    is_test: bool = False
    is_silent: bool = False