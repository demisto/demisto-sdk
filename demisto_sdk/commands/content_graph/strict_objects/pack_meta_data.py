from typing import List, Optional, Union

from packaging.version import Version
from pydantic import Field, validator

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class PackSupportOption(StrEnum):
    XSOAR_SUPPORT = "xsoar"
    PARTNER_SUPPORT = "partner"
    COMMUNITY_SUPPORT = "community"
    DEVELOPER_SUPPORT = "developer"


class StrictPackMetadata(BaseStrictModel):
    @validator("current_version")
    def is_valid_current_version(cls, value: str) -> str:
        """
        Validator ensures current_version field is valid.
        In case of invalid version, will raise exception and will be shown as a structure pydantic error
        """
        Version(value)
        return value

    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    legacy: Optional[bool] = None
    support: PackSupportOption
    url: Optional[str] = None
    email: Optional[str] = None
    eula_link: Optional[str] = Field(None, alias="eulaLink")
    author: str
    author_image: Optional[str] = Field(None, alias="authorImage")
    certification: Optional[str] = None
    price: Optional[int] = None
    hidden: Optional[bool] = None
    server_min_version: Optional[str] = Field(alias="serverMinVersion")
    current_version: Optional[str] = Field(alias="currentVersion")
    version_info: str = Field("", alias="versionInfo")
    commit: Optional[str] = None
    downloads: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list, alias="useCases")
    keywords: Optional[List[str]] = Field(default_factory=list)
    search_rank: Optional[int] = Field(None, alias="searchRank")
    excluded_dependencies: List[str] = Field(
        default_factory=list, alias="excludedDependencies"
    )
    videos: List[str] = Field(default_factory=list)
    modules: List[str] = Field(default_factory=list)
    integrations: Optional[List[str]] = Field(default_factory=list)
    hybrid: bool = Field(False, alias="hybrid")
    default_data_source_id: Optional[str] = Field(None, alias="defaultDataSource")
    default_data_source_name: Optional[str] = Field(None, exclude=True)
    beta: Optional[bool] = None
    dependencies: Optional[dict] = Field(default_factory=dict)
    deprecated: Optional[bool] = None
    marketplaces: Optional[List[MarketplaceVersions]] = None
    github_user: Optional[Union[str, List[str]]] = Field(
        alias="githubUser", default_factory=list
    )
    dev_email: Optional[Union[str, List[str]]] = Field(None, alias="devEmail")
    displayed_images: Optional[List[str]] = Field(None, alias="displayedImages")
    item_prefix: Optional[Union[str, List[str]]] = Field(None, alias="itemPrefix")
    from_version: Optional[str] = Field(None, alias="fromVersion")
    previous_name: Optional[str] = Field(None, alias="prevName")

    # For private packs
    premium: Optional[bool] = None
    vendor_id: Optional[str] = Field(None, alias="vendorId")
    partner_id: Optional[str] = Field(None, alias="partnerId")
    partner_name: Optional[str] = Field(None, alias="partnerName")
    preview_only: Optional[bool] = Field(None, alias="previewOnly")
    disable_monthly: Optional[bool] = Field(None, alias="disableMonthly")
    content_commit_hash: Optional[str] = Field(None, alias="contentCommitHash")
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")
