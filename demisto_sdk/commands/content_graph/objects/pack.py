import logging
import os
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Tuple

import demisto_client
from demisto_client.demisto_api.rest import ApiException
from packaging.version import Version, parse
from pydantic import BaseModel, DirectoryPath, Field, validator

from demisto_sdk.commands.common.constants import (
    BASE_PACK,
    CONTRIBUTORS_README_TEMPLATE,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    MARKETPLACE_MIN_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import MarketplaceTagParser
from demisto_sdk.commands.content_graph.common import (
    PACK_METADATA_FILENAME,
    ContentType,
    Nodes,
    PackTags,
    Relationships,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent,
)
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    NotIndivitudallyUploadableException,
)
from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.exceptions import (
    FailedUploadException,
    FailedUploadMultipleException,
)
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
from demisto_sdk.commands.content_graph.objects.pre_process_rule import PreProcessRule
from demisto_sdk.commands.content_graph.objects.report import Report
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.content_graph.objects.xdrc_template import XDRCTemplate
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport
from demisto_sdk.commands.upload.constants import (
    CONTENT_TYPES_EXCLUDED_FROM_UPLOAD,
    MULTIPLE_ZIPPED_PACKS_FILE_NAME,
    MULTIPLE_ZIPPED_PACKS_FILE_STEM,
)
from demisto_sdk.commands.upload.exceptions import IncompatibleUploadVersionException
from demisto_sdk.commands.upload.tools import (
    parse_error_response,
    parse_upload_response,
)

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData

logger = logging.getLogger("demisto-sdk")
json = JSON_Handler()

MINIMAL_UPLOAD_SUPPORTED_VERSION = Version("6.5.0")
MINIMAL_ALLOWED_SKIP_VALIDATION_VERSION = Version("6.6.0")


def upload_zip(
    path: Path,
    client: demisto_client,
    skip_validations: bool,
    target_demisto_version: Version,
    marketplace: MarketplaceVersions,
) -> bool:
    """
    Used to upload an existing zip file
    """
    if path.suffix != ".zip":
        raise RuntimeError(f"cannot upload {path} as zip")
    if (
        marketplace == MarketplaceVersions.XSOAR
        and target_demisto_version < MINIMAL_UPLOAD_SUPPORTED_VERSION
    ):
        raise RuntimeError(
            f"Uploading packs to XSOAR versions earlier than {MINIMAL_UPLOAD_SUPPORTED_VERSION} is no longer supported."
            "Use older versions of the Demisto-SDK for that (<=1.13.0)"
        )
    server_kwargs = {"skip_verify": "true"}

    if (
        skip_validations
        and target_demisto_version >= MINIMAL_ALLOWED_SKIP_VALIDATION_VERSION
    ):
        server_kwargs["skip_validation"] = "true"

    response = client.upload_content_packs(
        file=str(path),
        **server_kwargs,
    )
    if response is None:  # uploaded successfully
        return True

    parse_upload_response(
        response, path=path, content_type=ContentType.PACK
    )  # raises on error
    return True


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
    preprocess_rule: List[PreProcessRule] = Field(
        [], alias=ContentType.PREPROCESS_RULE.value
    )

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
    updated: Optional[str] = Field("")
    legacy: Optional[bool]
    support: Optional[str]
    url: Optional[str]
    email: Optional[str]
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
    tags: Optional[List[str]] = Field([])
    categories: Optional[List[str]]
    use_cases: Optional[List[str]] = Field(alias="useCases")
    keywords: Optional[List[str]]
    search_rank: Optional[int] = Field(alias="searchRank")
    excluded_dependencies: Optional[List[str]] = Field(alias="excludedDependencies")
    videos: Optional[List[str]] = Field([])
    modules: Optional[List[str]] = Field([])

    # For private packs
    premium: Optional[bool]
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
        return CONTENT_PATH / v

    @property
    def is_private(self) -> Optional[bool]:
        return self.premium or False

    @property
    def pack_id(self) -> str:
        return self.object_id

    @property
    def pack_name(self) -> str:
        return self.name

    @property
    def pack_version(self) -> Optional[Version]:
        return Version(self.current_version) if self.current_version else None

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

        # If there is no server_min_version, set it to the minimum of its content items fromversion
        min_content_items_version = MARKETPLACE_MIN_VERSION
        if content_items:
            min_content_items_version = str(
                min(parse(content_item.fromversion) for content_item in content_items)
            )
        self.server_min_version = self.server_min_version or min_content_items_version
        self.content_items = PackContentItems(**content_item_dct)

    def dump_metadata(self, path: Path, marketplace: MarketplaceVersions) -> None:
        self.server_min_version = self.server_min_version or MARKETPLACE_MIN_VERSION
        self.enhance_pack_properties(marketplace)

        excluded_fields_from_metadata = {
            "path",
            "node_id",
            "content_type",
            "url",
            "email",
            "database_id",
        }
        if not self.is_private:
            excluded_fields_from_metadata |= {
                "premium",
                "vendor_id",
                "partner_id",
                "partner_name",
                "preview_only",
                "disable_monthly",
            }

        metadata = self.dict(exclude=excluded_fields_from_metadata, by_alias=True)
        metadata.update(self.enhance_metadata(marketplace))

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

    def dump(
        self,
        path: Path,
        marketplace: MarketplaceVersions,
    ):
        if not self.path.exists():
            logger.warning(f"Pack {self.name} does not exist in {self.path}")
            return

        try:
            path.mkdir(exist_ok=True, parents=True)

            for content_item in self.content_items:
                if content_item.content_type in CONTENT_TYPES_EXCLUDED_FROM_UPLOAD:
                    logger.debug(
                        f"SKIPPING dump {content_item.content_type} {content_item.normalize_name}"
                        "whose type was passed in `exclude_content_types`"
                    )
                    continue

                if marketplace not in content_item.marketplaces:
                    logger.debug(
                        f"SKIPPING dump {content_item.content_type} {content_item.normalize_name}"
                        f"to destination {marketplace=}"
                        f" - content item has marketplaces {content_item.marketplaces}"
                    )
                    continue

                folder = content_item.content_type.as_folder
                if (
                    content_item.content_type == ContentType.SCRIPT
                    and content_item.is_test
                ):
                    folder = ContentType.TEST_PLAYBOOK.as_folder

                content_item.dump(
                    dir=path / folder,
                    marketplace=marketplace,
                )
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
                self._copy_base_pack_docs(path, marketplace)

            pack_files = "\n".join([str(f) for f in path.iterdir()])
            logger.info(f"Dumped pack {self.name}.")
            logger.debug(f"Pack {self.name} files:\n{pack_files}")

        except Exception:
            logger.exception(f"Failed dumping pack {self.name}")
            raise

    def upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
        target_demisto_version: Version,
        destination_zip_dir: Optional[Path] = None,
        zip: bool = False,
        **kwargs,
    ):
        if destination_zip_dir is None:
            raise ValueError("invalid destination_zip_dir=None")

        if zip:
            self._zip_and_upload(
                client=client,
                marketplace=marketplace,
                target_demisto_version=target_demisto_version,
                skip_validations=kwargs.get("skip_validations", False),
                destination_dir=destination_zip_dir,
            )
        else:
            self._upload_item_by_item(
                client=client,
                marketplace=marketplace,
                target_demisto_version=target_demisto_version,
            )

    def _zip_and_upload(
        self,
        client: demisto_client,
        target_demisto_version: Version,
        skip_validations: bool,
        marketplace: MarketplaceVersions,
        destination_dir: DirectoryPath,
    ) -> bool:
        # this should only be called from Pack.upload
        logger.debug(f"Uploading zipped pack {self.object_id}")

        # 1) dump the pack into a temporary file
        with TemporaryDirectory() as temp_dump_dir:
            temp_dir_path = Path(temp_dump_dir)
            self.dump(temp_dir_path, marketplace=marketplace)

            # 2) zip the dumped pack
            with TemporaryDirectory() as pack_zips_dir:
                pack_zip_path = Path(
                    shutil.make_archive(
                        str(Path(pack_zips_dir, self.name)), "zip", temp_dir_path
                    )
                )
                str(pack_zip_path)

                # 3) zip the zipped pack into uploadable_packs.zip under the result directory
                try:
                    shutil.make_archive(
                        str(destination_dir / MULTIPLE_ZIPPED_PACKS_FILE_STEM),
                        "zip",
                        pack_zips_dir,
                    )
                except Exception:
                    logger.exception(
                        f"Cannot write to {str(destination_dir / MULTIPLE_ZIPPED_PACKS_FILE_NAME)}"
                    )

                # upload the pack zip (not the result)
                return upload_zip(
                    path=pack_zip_path,
                    client=client,
                    target_demisto_version=target_demisto_version,
                    skip_validations=skip_validations,
                    marketplace=marketplace,
                )

    def _upload_item_by_item(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
        target_demisto_version: Version,
    ) -> bool:
        # this should only be called from Pack.upload
        logger.debug(
            f"Uploading pack {self.object_id} element-by-element, as -z was not specified"
        )
        upload_failures: List[FailedUploadException] = []
        uploaded_successfully: List[ContentItem] = []
        incompatible_content_items = []

        for item in self.content_items:
            if item.content_type in CONTENT_TYPES_EXCLUDED_FROM_UPLOAD:
                logger.debug(
                    f"SKIPPING upload of {item.content_type} {item.object_id}: type is skipped"
                )
                continue

            try:
                logger.debug(
                    f"uploading pack {self.object_id}: {item.content_type} {item.object_id}"
                )
                item.upload(
                    client=client,
                    marketplace=marketplace,
                    target_demisto_version=target_demisto_version,
                )
                uploaded_successfully.append(item)
            except NotIndivitudallyUploadableException:
                if marketplace == MarketplaceVersions.MarketplaceV2:
                    raise  # many XSIAM content types must be uploaded zipped.
                logger.warning(
                    f"Not uploading pack {self.object_id}: {item.content_type} {item.object_id} as it was not indivudally uploaded"
                )
            except ApiException as e:
                upload_failures.append(
                    FailedUploadException(
                        item.path,
                        response_body={},
                        additional_info=parse_error_response(e),
                    )
                )
            except IncompatibleUploadVersionException as e:
                incompatible_content_items.append(e)

            except FailedUploadException as e:
                upload_failures.append(e)

        if upload_failures or incompatible_content_items:
            raise FailedUploadMultipleException(
                uploaded_successfully, upload_failures, incompatible_content_items
            )

        return True

    def _copy_base_pack_docs(
        self, destination_path: Path, marketplace: MarketplaceVersions
    ):

        documentation_path = CONTENT_PATH / "Documentation"
        documentation_output = destination_path / "Documentation"
        documentation_output.mkdir(exist_ok=True, parents=True)
        if (
            marketplace.value
            and (documentation_path / f"doc-howto-{marketplace.value}.json").exists()
        ):
            shutil.copy(
                documentation_path / f"doc-howto-{marketplace.value}.json",
                documentation_output / "doc-howto.json",
            )
        elif (documentation_path / "doc-howto-xsoar.json").exists():
            shutil.copy(
                documentation_path / "doc-howto-xsoar.json",
                documentation_output / "doc-howto.json",
            )
        else:
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

    def enhance_pack_properties(self, marketplace: MarketplaceVersions):
        self.tags = self.get_pack_tags(marketplace)
        self.commit = self.get_last_commit()
        self.version_info = os.environ.get("CI_PIPELINE_ID", "")
        self.server_min_version = (
            self.server_min_version
            or str(
                max(
                    (
                        parse(content_item.fromversion)
                        for content_item in self.content_items
                    ),
                    default=MARKETPLACE_MIN_VERSION,
                )
            )
            or MARKETPLACE_MIN_VERSION
        )

    def enhance_metadata(self, marketplace: MarketplaceVersions) -> dict:
        _metadata: dict = {}

        content_items, content_displays = self.get_content_items_and_displays_metadata(
            marketplace
        )
        support_details = {"url": self.url}
        if self.email:
            support_details["email"] = self.email

        _metadata.update(
            {
                "contentItems": content_items,
                "contentDisplays": content_displays,
                "dependencies": self.enhance_dependencies(),
                "supportDetails": support_details,
            }
        )

        return _metadata

    def get_content_items_and_displays_metadata(
        self, marketplace: MarketplaceVersions
    ) -> Tuple[Dict, Dict]:
        content_items: dict = {}
        content_displays: dict = {}
        for content_item in self.content_items:

            if content_item.content_type == ContentType.TEST_PLAYBOOK:
                logger.debug(
                    f"Skip loading the {content_item.name} test playbook into metadata.json"
                )
                continue

            try:
                if content_item.is_incident_to_alert(marketplace):
                    content_item_summary = content_item.summary(
                        marketplace, incident_to_alert=True
                    )
                else:
                    content_item_summary = content_item.summary(marketplace)

                content_items.setdefault(content_item.content_type.metadata_name, [])

                if is_item_metadata_appended := [
                    c
                    for c in content_items[content_item.content_type.metadata_name]
                    if c.get("id") == content_item.object_id
                ]:
                    content_item_metadata = is_item_metadata_appended[0]

                    if parse(content_item.toversion) > parse(
                        content_item_metadata["toversion"]
                        or DEFAULT_CONTENT_ITEM_TO_VERSION
                    ):
                        content_item_metadata.update(content_item_summary.items())

                        if content_item.toversion == DEFAULT_CONTENT_ITEM_TO_VERSION:
                            content_item_metadata["toversion"] = ""
                else:
                    content_item_summary["toversion"] = (
                        content_item_summary["toversion"]
                        if content_item_summary["toversion"]
                        != DEFAULT_CONTENT_ITEM_TO_VERSION
                        else ""
                    )
                    content_items[content_item.content_type.metadata_name].append(
                        content_item_summary
                    )

                content_displays[content_item.content_type.metadata_name] = content_item.content_type.metadata_display_name  # type: ignore[index]
            except NotImplementedError as e:
                logger.debug(f"Could not add {content_item.name} to pack metadata: {e}")
            except TypeError as e:
                raise Exception(
                    f"Could not set metadata_name of type {content_item.content_type.metadata_name} - "
                    f"{content_item.content_type.metadata_display_name} in {content_displays}\n{e}"
                )

        content_displays = {
            content_type: content_type_display
            if len(content_items[content_type]) == 1
            else f"{content_type_display}s"
            for content_type, content_type_display in content_displays.items()
        }  # type: ignore[union-attr]

        return content_items, content_displays

    def enhance_dependencies(self):
        return {
            r.content_item_to.object_id: {
                "mandatory": r.mandatorily,
                "minVersion": r.content_item_to.current_version,  # type:ignore[attr-defined]
                "author": r.content_item_to.author,  # type:ignore[attr-defined]
                "name": r.content_item_to.name,  # type:ignore[attr-defined]
                "certification": r.content_item_to.certification,  # type:ignore[attr-defined]
            }
            for r in self.depends_on
            if r.is_direct
        }

    @staticmethod
    def get_last_commit():
        return GitUtil().get_current_commit_hash()

    def get_pack_tags(self, marketplace):
        tags = self.get_tags_by_marketplace(marketplace)
        tags |= (
            {PackTags.TIM}
            if any(
                [integration.is_feed for integration in self.content_items.integration]
            )
            or any(
                [
                    playbook.name.startswith("TIM ")
                    for playbook in self.content_items.playbook
                ]
            )
            else set()
        )
        tags |= {PackTags.USE_CASE} if self.use_cases else set()
        tags |= (
            {PackTags.TRANSFORMER}
            if any(
                ["transformer" in script.tags for script in self.content_items.script]
            )
            else set()
        )
        tags |= (
            {PackTags.FILTER}
            if any(["filter" in script.tags for script in self.content_items.script])
            else set()
        )
        tags |= (
            {PackTags.COLLECTION}
            if any(
                [
                    integration.is_fetch_events
                    for integration in self.content_items.integration
                ]
            )
            or any(
                [
                    self.content_items.parsing_rule,
                    self.content_items.modeling_rule,
                    self.content_items.correlation_rule,
                    self.content_items.xdrc_template,
                ]
            )
            else set()
        )
        tags |= (
            {PackTags.DATA_SOURCE}
            if self.is_data_source()
            and marketplace == MarketplaceVersions.MarketplaceV2
            else set()
        )

        if self.created:
            days_since_creation = (
                datetime.utcnow()
                - datetime.strptime(self.created, "%Y-%m-%dT%H:%M:%SZ")
            ).days
            if days_since_creation <= 30:
                tags |= {PackTags.NEW}
            else:
                tags -= {PackTags.NEW}

        return list(tags)

    def get_tags_by_marketplace(self, marketplace: str):
        """Returns tags in according to the current marketplace"""
        tags: set = set()

        if not self.tags:
            return tags

        for tag in self.tags:
            if ":" in tag:
                tag_data = tag.split(":")
                if marketplace in tag_data[0].split(","):
                    tags.update({tag_data[1]})
            else:
                tags.update({tag})

        return tags

    def is_data_source(self):
        return (
            len(
                [
                    MarketplaceVersions.MarketplaceV2 in integration.marketplaces
                    and not integration.deprecated
                    and (integration.is_fetch or integration.is_fetch_events)
                    for integration in self.content_items.integration
                ]
            )
            == 1
        )
