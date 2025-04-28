from datetime import datetime
from typing import Optional, Any

from pydantic import Field, DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import write_dict, get_file
from demisto_sdk.commands.content_graph.common import replace_marketplace_references, append_supported_modules
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import MarketplaceSuffixPreparer

from demisto_sdk.commands.common.handlers import (
    JSON_Handler,
    XSOAR_Handler,
    YAML_Handler,
)


class AgentixBase(BaseContent):
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
    display: str = Field(..., alias="name")
    description: str
    pack: Any = Field(None, exclude=True, repr=False)
    is_test: bool = False

    @property
    def data(self) -> dict:
        return get_file(self.path, keep_order=False)

    @property
    def handler(self) -> XSOAR_Handler:
        # we use a high value so the code lines will not break
        return (
            JSON_Handler()
            if self.path.suffix.lower() == ".json"
            else YAML_Handler(width=50_000)
        )

    def prepare_for_upload(
            self,
            current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
            **kwargs,
    ) -> dict:
        if not self.path.exists():
            raise FileNotFoundError(f"Could not find file {self.path}")
        data = self.data
        # Replace incorrect marketplace references
        data = replace_marketplace_references(data, current_marketplace, str(self.path))
        if current_marketplace == MarketplaceVersions.PLATFORM:
            data = append_supported_modules(data, self.supportedModules)
        else:
            if "supportedModules" in data:
                del data["supportedModules"]
        return MarketplaceSuffixPreparer.prepare(data, current_marketplace)

    def dump(
            self,
            dir: DirectoryPath,
            marketplace: MarketplaceVersions,
    ) -> None:
        if not self.path.exists():
            logger.warning(f"Could not find file {self.path}, skipping dump")
            return
        dir.mkdir(exist_ok=True, parents=True)
        try:
            write_dict(
                dir / self.normalize_name,
                data=self.prepare_for_upload(current_marketplace=marketplace),
                handler=self.handler,
            )
            logger.debug(f"path to dumped file: {str(dir / self.normalize_name)}")
        except FileNotFoundError as e:
            logger.warning(f"Failed to dump {self.path} to {dir}: {e}")
