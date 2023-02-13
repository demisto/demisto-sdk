import logging
import shutil
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, List, Optional

from packaging.version import parse
from pydantic import BaseModel, Field, validator

from demisto_sdk.commands.common.constants import (
    BASE_PACK,
    CONTRIBUTORS_README_TEMPLATE,
    MARKETPLACE_MIN_VERSION,
    MarketplaceVersions,
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
from demisto_sdk.commands.content_graph.objects.layout_rule import LayoutRule
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
    layout_rule: List[LayoutRule] = Field([], alias=ContentType.LAYOUT_RULE.value)

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
    description: Optional[str]
    created: Optional[str]
    updated: Optional[str]
    support: Optional[str]
    email: Optional[str]
    url: Optional[str]
    author: Optional[str]
    certification: Optional[str]
    hidden: Optional[bool]
    server_min_version: Optional[str] = Field(alias="serverMinVersion")
    current_version: Optional[str] = Field(alias="currentVersion")
    tags: Optional[List[str]]
    categories: Optional[List[str]]
    use_cases: Optional[List[str]] = Field(alias="useCases")
    keywords: Optional[List[str]]
    price: Optional[int] = None
    premium: Optional[bool] = None
    vendor_id: Optional[str] = Field(None, alias="vendorId")
    vendor_name: Optional[str] = Field(None, alias="vendorName")
    preview_only: Optional[bool] = Field(None, alias="previewOnly")
    excluded_dependencies: Optional[List[str]]


class Pack(BaseContent, PackMetadata, content_type=ContentType.PACK):  # type: ignore[call-arg]
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
        return CONTENT_PATH / v

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
        metadata = self.dict(
            exclude={"path", "node_id", "content_type", "excluded_dependencies"}
        )
        metadata["contentItems"] = {}
        for content_item in self.content_items:
            try:
                metadata["contentItems"].setdefault(
                    content_item.content_type.server_name, []
                ).append(content_item.summary(marketplace))
            except NotImplementedError as e:
                logger.debug(f"Could not add {content_item.name} to pack metadata: {e}")
        with open(path, "w") as f:
            json.dump(metadata, f, indent=4)

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
                logger.debug(f'No such file {self.path / "ReleaseNotes"}')
            try:
                shutil.copy(self.path / "Author_image.png", path / "Author_image.png")
            except FileNotFoundError:
                logger.debug(f'No such file {self.path / "Author_image.png"}')
            if self.object_id == BASE_PACK:
                self.handle_base_pack(path)

            pack_files = "\n".join([str(f) for f in path.iterdir()])
            logger.info(f"Dumped pack {self.name}.")
            logger.debug(f"Pack {self.name} files:\n{pack_files}")
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
