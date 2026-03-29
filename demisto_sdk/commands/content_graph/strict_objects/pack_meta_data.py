from typing import List, Optional, Union

from packaging.version import Version
from pydantic import Field, root_validator, validator

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

    @root_validator
    def validate_managed_pack_has_source(cls, values):
        """
        Validator ensures that packs with managed: true have a non-empty source field.
        This validation will be shown as a structure pydantic error (ST110).
        """
        managed = values.get("managed", False)
        source = values.get("source", "")

        if managed and not source:
            raise ValueError(
                "Pack has 'managed: true' but is missing a non-empty 'source' field. "
                "Managed packs must specify their source to maintain proper attribution and tracking."
            )

        return values

    name: str = Field(
        ...,
        description="Unique machine-readable name of the pack. Used as the pack directory name and in API references. Must not contain spaces.",
    )
    display_name: Optional[str] = Field(
        None,
        description="Human-readable display name of the pack shown in the marketplace. Can contain spaces and special characters.",
    )
    description: Optional[str] = Field(
        None,
        description="Short description of the pack shown in the marketplace listing. Should be concise (1-2 sentences).",
    )
    created: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp of when this pack was first created. Set automatically.",
    )
    updated: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp of when this pack was last updated. Set automatically.",
    )
    legacy: Optional[bool] = Field(
        None,
        description="When True, marks this pack as a legacy pack that is no longer actively maintained.",
    )
    support: PackSupportOption = Field(
        ...,
        description="Support level for this pack. Must be one of: 'xsoar' (Palo Alto Networks), 'partner' (technology partner), 'community' (community-maintained), 'developer' (individual developer).",
    )
    url: Optional[str] = Field(
        None,
        description="URL to the pack's support page or documentation. Shown in the marketplace listing.",
    )
    email: Optional[str] = Field(
        None,
        description="Support email address for this pack. Shown in the marketplace listing.",
    )
    eula_link: Optional[str] = Field(
        None,
        alias="eulaLink",
        description="URL to the End User License Agreement (EULA) for this pack. Required for paid packs.",
    )
    author: str = Field(
        ...,
        description="Name of the pack author or organization. Shown in the marketplace listing.",
    )
    author_image: Optional[str] = Field(
        None,
        alias="authorImage",
        description="Path to the author's logo image file within the pack. Shown in the marketplace listing.",
    )
    certification: Optional[str] = Field(
        None,
        description="Certification level of the pack (e.g. 'certified'). Indicates the pack has passed quality review.",
    )
    price: Optional[int] = Field(
        None,
        description="Price of the pack in marketplace credits. Set to 0 or omit for free packs.",
    )
    hidden: Optional[bool] = Field(
        None,
        description="When True, the pack is hidden from the marketplace listing but can still be installed directly.",
    )
    server_min_version: Optional[str] = Field(
        ...,
        alias="serverMinVersion",
        description="Minimum XSOAR/XSIAM server version required to install this pack (e.g. '6.0.0').",
    )
    current_version: Optional[str] = Field(
        ...,
        alias="currentVersion",
        description="Current semantic version of the pack (e.g. '1.2.3'). Must follow semver format. Increment on each release.",
    )
    version_info: str = Field(
        "",
        alias="versionInfo",
        description="Additional version information or release notes summary. Set automatically during release.",
    )
    commit: Optional[str] = Field(
        None,
        description="Git commit hash of the pack's last release. Set automatically during release.",
    )
    downloads: Optional[int] = Field(
        None,
        description="Number of times this pack has been downloaded from the marketplace. Set automatically.",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="List of tags for marketplace filtering and discovery (e.g. ['Threat Intelligence', 'Malware']). Use existing tags when possible.",
    )
    categories: List[str] = Field(
        default_factory=list,
        description="List of marketplace categories this pack belongs to (e.g. ['Data Enrichment & Threat Intelligence']). Must use valid category names.",
    )
    use_cases: List[str] = Field(
        default_factory=list,
        alias="useCases",
        description="List of use cases this pack addresses (e.g. ['Phishing', 'Malware']). Helps users discover relevant packs.",
    )
    keywords: Optional[List[str]] = Field(
        default_factory=list,
        description="Additional keywords for marketplace search. Supplements tags and categories.",
    )
    search_rank: Optional[int] = Field(
        None,
        alias="searchRank",
        description="Manual search ranking boost for this pack in marketplace search results. Higher values appear first.",
    )
    excluded_dependencies: List[str] = Field(
        default_factory=list,
        alias="excludedDependencies",
        description="List of pack names to exclude from automatic dependency resolution. Use when a dependency is optional or causes conflicts.",
    )
    videos: List[str] = Field(
        default_factory=list,
        description="List of URLs to demo or tutorial videos for this pack. Shown in the marketplace listing.",
    )
    modules: List[str] = Field(
        default_factory=list,
        description="List of platform modules this pack is compatible with. Used for module-specific marketplace filtering.",
    )
    integrations: Optional[List[str]] = Field(
        default_factory=list,
        description="List of integration names included in this pack. Used for marketplace display.",
    )
    hybrid: bool = Field(
        False,
        alias="hybrid",
        description="When True, this pack supports both XSOAR and XSIAM platforms simultaneously.",
    )
    default_data_source_id: Optional[str] = Field(
        None,
        alias="defaultDataSource",
        description="ID of the default data source integration in this pack. Used for automatic data source configuration.",
    )
    default_data_source_name: Optional[str] = Field(
        None,
        exclude=True,
        description="Display name of the default data source. Derived from defaultDataSource. Not stored in pack_metadata.json.",
    )
    beta: Optional[bool] = Field(
        None,
        description="When True, marks this pack as a beta release. Beta packs may have limited support and are subject to change.",
    )
    dependencies: Optional[dict] = Field(
        default_factory=dict,
        description="Dictionary of pack dependencies. Keys are pack names, values are dependency metadata including mandatory flag and display name.",
    )
    deprecated: Optional[bool] = Field(
        None,
        description="When True, this pack is deprecated and users should migrate to a replacement pack.",
    )
    marketplaces: Optional[List[MarketplaceVersions]] = Field(
        None,
        description="Marketplace(s) this pack is available in. Allowed values: xsoar, marketplacev2, xpanse, xsoar_saas, xsoar_on_prem, platform.",
    )
    github_user: Optional[Union[str, List[str]]] = Field(
        alias="githubUser",
        default_factory=list,
        description="GitHub username(s) of the pack maintainer(s). Used for contribution tracking.",
    )
    dev_email: Optional[Union[str, List[str]]] = Field(
        None,
        alias="devEmail",
        description="Developer email address(es) for internal communication. Not shown publicly.",
    )
    displayed_images: Optional[List[str]] = Field(
        None,
        alias="displayedImages",
        description="List of integration names whose logos are displayed in the pack's marketplace listing.",
    )
    item_prefix: Optional[Union[str, List[str]]] = Field(
        None,
        alias="itemPrefix",
        description="Prefix(es) used for content item names in this pack. Helps avoid naming conflicts.",
    )
    from_version: Optional[str] = Field(
        None,
        alias="fromVersion",
        description="Minimum platform version required to install this pack (e.g. '6.0.0').",
    )
    previous_name: Optional[str] = Field(
        None,
        alias="prevName",
        description="Previous name of this pack before it was renamed. Used for migration and backward compatibility.",
    )
    # For private packs
    premium: Optional[bool] = Field(
        None,
        description="When True, this is a premium (paid) pack available only to subscribers.",
    )
    vendor_id: Optional[str] = Field(
        None,
        alias="vendorId",
        description="Vendor identifier for premium packs. Used for billing and access control.",
    )
    partner_id: Optional[str] = Field(
        None,
        alias="partnerId",
        description="Partner identifier for partner-supported packs. Used for partner portal integration.",
    )
    partner_name: Optional[str] = Field(
        None,
        alias="partnerName",
        description="Display name of the technology partner who created this pack.",
    )
    preview_only: Optional[bool] = Field(
        None,
        alias="previewOnly",
        description="When True, this pack is in preview mode and not yet generally available.",
    )
    disable_monthly: Optional[bool] = Field(
        None,
        alias="disableMonthly",
        description="When True, disables monthly billing for this premium pack.",
    )
    content_commit_hash: Optional[str] = Field(
        None,
        alias="contentCommitHash",
        description="Git commit hash of the content repository at the time of pack release.",
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this pack. Restricts availability to specific modules.",
    )
    source: Optional[str] = Field(
        "",
        alias="source",
        description="Source repository or origin of this pack. Required when managed=True. Identifies where the pack content is maintained.",
    )
    managed: Optional[bool] = Field(
        False,
        alias="managed",
        description="When True, this pack is managed externally and its content is synchronized from the source repository. Requires a non-empty source field.",
    )
