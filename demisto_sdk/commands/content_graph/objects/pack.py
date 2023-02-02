import logging
import shutil
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, List, Optional, Dict
from datetime import datetime

from packaging.version import parse
from pydantic import BaseModel, Field, validator

from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.constants import (
    BASE_PACK,
    CONTRIBUTORS_README_TEMPLATE,
    MARKETPLACE_MIN_VERSION,
    MarketplaceVersions,
    MARKETPLACE_MIN_VERSION,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import MarketplaceTagParser
from demisto_sdk.commands.content_graph.common import (
    PACK_METADATA_FILENAME,
    ContentType,
    Nodes,
    Relationships,
    RelationshipType,
    PackTags,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.generic_definition import (
    GenericDefinition,
)
from demisto_sdk.commands.content_graph.objects.generic_field import GenericField
from demisto_sdk.commands.content_graph.objects.generic_module import GenericModule
from demisto_sdk.commands.content_graph.objects.generic_type import GenericType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.job import Job
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.list import List as ListObject
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.report import Report
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.content_graph.objects.xdrc_template import XDRCTemplate
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData

logger = logging.getLogger("demisto-sdk")
json = JSON_Handler()


class PackContentItems(BaseModel):
    # The alias is for marshalling purposes
    classifier: List[Classifier] = Field([], alias=ContentType.CLASSIFIER.value)
    correlation_rule: List[CorrelationRule] = Field(
        [], alias=ContentType.CORRELATION_RULE.value
    )
    dashboard: List[Dashboard] = Field([], alias=ContentType.DASHBOARD.value)
    generic_definition: List[GenericDefinition] = Field(
        [], alias=ContentType.GENERIC_DEFINITION.value
    )
    generic_field: List[GenericField] = Field([], alias=ContentType.GENERIC_FIELD.value)
    generic_module: List[GenericModule] = Field(
        [], alias=ContentType.GENERIC_MODULE.value
    )
    generic_type: List[GenericType] = Field([], alias=ContentType.GENERIC_TYPE.value)
    incident_field: List[IncidentField] = Field(
        [], alias=ContentType.INCIDENT_FIELD.value
    )
    incident_type: List[IncidentType] = Field([], alias=ContentType.INCIDENT_TYPE.value)
    indicator_field: List[IndicatorField] = Field(
        [], alias=ContentType.INDICATOR_FIELD.value
    )
    indicator_type: List[IndicatorType] = Field(
        [], alias=ContentType.INDICATOR_TYPE.value
    )
    integration: List[Integration] = Field([], alias=ContentType.INTEGRATION.value)
    job: List[Job] = Field([], alias=ContentType.JOB.value)
    layout: List[Layout] = Field([], alias=ContentType.LAYOUT.value)
    list: List[ListObject] = Field([], alias=ContentType.LIST.value)
    mapper: List[Mapper] = Field([], alias=ContentType.MAPPER.value)
    modeling_rule: List[ModelingRule] = Field([], alias=ContentType.MODELING_RULE.value)
    parsing_rule: List[ParsingRule] = Field([], alias=ContentType.PARSING_RULE.value)
    playbook: List[Playbook] = Field([], alias=ContentType.PLAYBOOK.value)
    report: List[Report] = Field([], alias=ContentType.REPORT.value)
    script: List[Script] = Field([], alias=ContentType.SCRIPT.value)
    test_playbook: List[TestPlaybook] = Field([], alias=ContentType.TEST_PLAYBOOK.value)
    trigger: List[Trigger] = Field([], alias=ContentType.TRIGGER.value)
    widget: List[Widget] = Field([], alias=ContentType.WIDGET.value)
    wizard: List[Wizard] = Field([], alias=ContentType.WIZARD.value)
    xsiam_dashboard: List[XSIAMDashboard] = Field(
        [], alias=ContentType.XSIAM_DASHBOARD.value
    )
    xsiam_report: List[XSIAMReport] = Field([], alias=ContentType.XSIAM_REPORT.value)
    xdrc_template: List[XDRCTemplate] = Field([], alias=ContentType.XDRC_TEMPLATE.value)

    def __iter__(self) -> Generator[ContentItem, Any, Any]:  # type: ignore
        """Defines the iteration of the object. Each iteration yields a single content item."""
        for content_items in vars(self).values():
            yield from content_items

    def __bool__(self) -> bool:
        """Used for easier determination of content items existence in a pack."""
        return bool(list(self))

    class Config:
        arbitrary_types_allowed = True
        orm_mode = True
        allow_population_by_field_name = True


class PackMetadata(BaseModel):
    name: str
    id: Optional[str]
    description: Optional[str]
    created: Optional[str]
    updated: Optional[str]
    legacy: Optional[bool]
    support: Optional[str]
    url: Optional[str]
    email: Optional[str]
    support_details: Optional[dict] = Field(alias="supportDetails")
    eulaLink: Optional[str]
    author: Optional[str]
    authorImage: Optional[str]
    certification: Optional[str]
    price: Optional[int]
    hidden: Optional[bool]
    server_min_version: Optional[str] = Field(alias="serverMinVersion")
    current_version: Optional[str] = Field(alias="currentVersion")
    version_info: Optional[str] = Field("", alias="versionInfo")
    commit: Optional[str]
    downloads: Optional[int]
    tags: Optional[List[str]]
    categories: Optional[List[str]]
    use_cases: Optional[List[str]] = Field(alias="useCases")
    keywords: Optional[List[str]]
    content_displays: Optional[Dict[str, str]] = Field({}, alias="contentDisplays")
    search_rank: Optional[int] = Field(alias="searchRank")
    integrations: Optional[List[Dict[str, str]]]
    dependencies: Optional[Dict[str, dict]]
    excluded_dependencies: Optional[Dict[str, dict]] = Field(alias="excludedDependencies")
    videos: Optional[List[str]]

    # For private packs
    premium: bool
    vendor_id: Optional[str] = Field(None, alias="vendorId")
    partner_id: Optional[str] = Field(None, alias="partnerId")
    partner_name: Optional[str] = Field(None, alias="partnerName")
    preview_only: Optional[bool] = Field(None, alias="previewOnly")
    disable_monthly: Optional[bool] = Field(None, alias="disableMonthly")


class Pack(BaseContent, PackMetadata, content_type=ContentType.PACK):
    path: Path
    contributors: Optional[List[str]] = None
    relationships: Relationships = Field(Relationships(), exclude=True)

    content_items: PackContentItems = Field(
        PackContentItems(), alias="contentItems", exclude=True
    )

    @validator("path", always=True)
    def validate_path(cls, v: Path) -> Path:
        if v.is_absolute():
            return v
        return Path(CONTENT_PATH) / v

    @property
    def is_private(self) -> bool:
        return self.premium

    @property
    def depends_on(self) -> List["RelationshipData"]:
        """
        This returns the packs which this content item depends on.
        In addition, we can tell if it's a mandatorily dependency or not.

        Returns:
            List[RelationshipData]:
                RelationshipData:
                    relationship_type: RelationshipType
                    source: BaseContent
                    target: BaseContent

                    # this is the attribute we're interested in when querying
                    content_item: BaseContent

                    # Whether the relationship between items is direct or not
                    is_direct: bool

                    # Whether using the command mandatorily (or optional)
                    mandatorily: bool = False

        """
        return [
            r
            for r in self.relationships_data[RelationshipType.DEPENDS_ON]
            if r.content_item_to.database_id == r.target_id
        ]

    @property
    def dependent_packs(self):
        return [r for r in self.depends_on if r.content_item.content_type == ContentType.PACK]

    def set_content_items(self):
        content_items: List[ContentItem] = [
            r.content_item_to  # type: ignore[misc]
            for r in self.relationships_data[RelationshipType.IN_PACK]
            if r.content_item_to.database_id == r.source_id
        ]
        content_item_dct = defaultdict(list)
        for c in content_items:
            content_item_dct[c.content_type.value].append(c)

        # If there is no server_min_version, set it to the maximum of its content items fromversion
        max_content_items_version = MARKETPLACE_MIN_VERSION
        if content_items:
            max_content_items_version = str(
                max(parse(content_item.fromversion) for content_item in content_items)
            )
        self.server_min_version = self.server_min_version or max_content_items_version
        self.content_items = PackContentItems(**content_item_dct)

    def dump_metadata(self, path: Path, marketplace: MarketplaceVersions) -> None:
        content_items: dict = {}
        for content_item in self.content_items:
            try:
                content_items.setdefault(
                    content_item.content_type.metadata_name, []
                ).append(content_item.summary(marketplace))
                self.content_displays[content_item.content_type.metadata_name] = content_item.content_type.metadata_display_name  # type: ignore[index]
            except NotImplementedError as e:
                logger.debug(f"Could not add {content_item.name} to pack metadata: {e}")
            except TypeError as e:
                raise Exception(f"Could not set metadata_name of type {content_item.content_type} - {content_item.content_type.metadata_name} - {content_item.content_type.metadata_display_name} in {self.content_displays}\n{e}")

        self.content_displays = {content_type: content_type_display if len(content_items[content_type]) == 1 else f"{content_type_display}s"
                                 for content_type, content_type_display in self.content_displays.items()}  # type: ignore[union-attr]
        self.tags = self.get_pack_tags(marketplace)
        self.server_min_version = self.server_min_version or str(
            max((parse(content_item.fromversion) for content_item in self.content_items), default=MARKETPLACE_MIN_VERSION)
        ) or MARKETPLACE_MIN_VERSION

        # self.dependencies = self.enhance_dependencies()

        excluded_fields_from_metadata = {"path", "node_id", "content_type", "url", "email"}
        if not self.is_private:
            excluded_fields_from_metadata |= {"premium", "vendor_id", "partner_id", "partner_name", "preview_only", "disable_monthly"}
        metadata = self.dict(exclude=excluded_fields_from_metadata, by_alias=True)

        metadata["contentItems"] = content_items
        metadata["commit"] = self.get_last_commit()
        metadata["dependencies"] = self.enhance_dependencies()
        metadata["support_details"] = {"url": self.url}
        if self.email:
            metadata["support_details"]["email"] = self.email

        with open(path, "w") as f:
            json.dump(metadata, f, indent=4, sort_keys=True)

    def dump_readme(self, path: Path, marketplace: MarketplaceVersions) -> None:
        shutil.copyfile(self.path / "README.md", path)
        if self.contributors:
            fixed_contributor_names = [
                f" - {contrib_name}\n" for contrib_name in self.contributors
            ]
            contribution_data = CONTRIBUTORS_README_TEMPLATE.format(
                contributors_names="".join(fixed_contributor_names)
            )
            with open(path, "a+") as f:
                f.write(contribution_data)
        with open(path, "r+") as f:
            try:
                text = f.read()
                parsed_text = MarketplaceTagParser(marketplace).parse_text(text)
                if len(text) != len(parsed_text):
                    f.seek(0)
                    f.write(parsed_text)
                    f.truncate()
            except Exception as e:
                logger.error(f"Failed dumping readme: {e}")

    def dump(self, path: Path, marketplace: MarketplaceVersions):
        try:
            path.mkdir(exist_ok=True, parents=True)
            for content_item in self.content_items:
                folder = content_item.content_type.as_folder
                if (
                    content_item.content_type == ContentType.SCRIPT
                    and content_item.is_test
                ):
                    folder = ContentType.TEST_PLAYBOOK.as_folder
                content_item.dump(path / folder, marketplace)
            self.dump_metadata(path / "metadata.json", marketplace)
            self.dump_readme(path / "README.md", marketplace)
            shutil.copy(
                self.path / PACK_METADATA_FILENAME, path / PACK_METADATA_FILENAME
            )
            try:
                shutil.copytree(self.path / "ReleaseNotes", path / "ReleaseNotes")
            except FileNotFoundError:
                logger.info(f'No such file {self.path / "ReleaseNotes"}')
            try:
                shutil.copy(self.path / "Author_image.png", path / "Author_image.png")
            except FileNotFoundError:
                logger.info(f'No such file {self.path / "Author_image.png"}')
            if self.object_id == BASE_PACK:
                self.handle_base_pack(path)

            logger.info(f"Dumped pack {self.name}. Files: {list(path.iterdir())}")
        except Exception as e:
            logger.error(f"Failed dumping pack {self.name}: {e}")
            raise

    def handle_base_pack(self, path: Path):
        documentation_path = CONTENT_PATH / "Documentation"
        documentation_output = path / "Documentation"
        documentation_output.mkdir(exist_ok=True, parents=True)
        shutil.copy(
            documentation_path / "doc-howto.json",
            documentation_output / "doc-howto.json",
        )
        if (documentation_path / "doc-CommonServer.json").exists():
            shutil.copy(
                documentation_path / "doc-CommonServer.json",
                documentation_output / "doc-CommonServer.json",
            )

    def to_nodes(self) -> Nodes:
        return Nodes(
            self.to_dict(),
            *[content_item.to_dict() for content_item in self.content_items],
        )

    def enhance_dependencies(self):
        return {r.content_item.object_id: {
            "mandatory": r.mandatorily,
            "minVersion": r.content_item.server_min_version,
            "author": r.content_item.author,
            "name": r.content_item.name,
            "certification": r.content_item.certification
        } for r in self.dependent_packs}

    @staticmethod
    def get_last_commit():
        return GitUtil().get_current_commit_hash()

    def get_pack_tags(self, marketplace):
        tags = self.get_tags_by_marketplace(marketplace)
        tags |= {PackTags.TIM} if any([integration.is_feed for integration in self.content_items.integration]) or \
            any([playbook.name.startswith('TIM ') for playbook in self.content_items.playbook]) else set()
        tags |= {PackTags.USE_CASE} if self.use_cases else set()
        tags |= {PackTags.TRANSFORMER} if any(['transformer' in script.tags for script in self.content_items.script]) else set()
        tags |= {PackTags.FILTER} if any(['filter' in script.tags for script in self.content_items.script]) else set()
        tags |= {PackTags.COLLECTION} if any([integration.is_fetch_events for integration in self.content_items.integration]) or \
            any([self.content_items.parsing_rule, self.content_items.modeling_rule, self.content_items.correlation_rule,
                 self.content_items.xdrc_template]) else set()
        tags |= {PackTags.DATA_SOURCE} if self.is_data_source() and marketplace == MarketplaceVersions.MarketplaceV2 else set()

        if self.created:
            days_since_creation = (datetime.utcnow() - datetime.strptime(self.created, '%Y-%m-%dT%H:%M:%SZ')).days
            if days_since_creation <= 30:
                tags |= {PackTags.NEW}
            else:
                tags -= {PackTags.NEW}

        return list(tags)

    def get_tags_by_marketplace(self, marketplace: str):
        """ Returns tags in according to the current marketplace"""
        tags: set = set()
        for tag in self.tags:
            if ':' in tag:
                tag_data = tag.split(':')
                if marketplace in tag_data[0].split(','):
                    tags.update({tag_data[1]})
            else:
                tags.update({tag})

        return tags

    def is_data_source(self):
        return len([MarketplaceVersions.MarketplaceV2 in integration.marketplaces and
                    not integration.deprecated and
                    (integration.is_fetch or integration.is_fetch_events)
                    for integration in self.content_items.integration]) == 1
