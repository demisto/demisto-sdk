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
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
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
    integrations: Optional[List[str]] = Field([])

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
    deprecated: bool = False
    content_items: PackContentItems = Field(
        PackContentItems(), alias="contentItems", exclude=True
    )

    @validator("path", always=True)
    def validate_path(cls, v: Path) -> Path:
        if v.is_absolute():
            return v
        return CONTENT_PATH / v

    @property
    def is_private(self) -> bool:
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
        """Dumps the pack metadata file.

        Args:
            path (Path): The path of the file to dump the metadata.
            marketplace (MarketplaceVersions): The marketplace to which the pack should belong to.
        """
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
        """
        Enhancing the Pack object properties before dumping into a dictionary.
        - Adding tags considering the pack content items and marketplace.
        - Replacing the `author` property from XSOAR to XSIAM if the prepare is to marketplacev2.
        - Getting into the `version_info` property the pipeline_id variable.
        - Calculating the `server_min_version` by the pack's content items fromversion`.

        Args:
            marketplace (MarketplaceVersions): The marketplace to which the pack should belong to.
        """
        self.tags = self.get_pack_tags(marketplace)
        self.author = (
            self.author
            if marketplace == MarketplaceVersions.XSOAR
            else self.author.replace("XSOAR", "XSIAM")  # type:ignore[union-attr]
        )
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
        """
        Enhancing the pack metadata properties after dumping into a dictionary. (properties that can't be calculating before)
        - Adding the pack's content items and calculating their from/to version before.
        - Adding the content items display names.
        - Gathering the pack dependencies and adding the metadata.
        - Unifying the `url` and `email` into the `support_details` property.

        Args:
            marketplace (MarketplaceVersions): The marketplace to which the pack should belong to.

        Returns:
            dict: The update metadata dictionary.
        """
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
                "dependencies": self.enhance_dependencies(marketplace),
                "supportDetails": support_details,
            }
        )

        return _metadata

    def get_content_items_and_displays_metadata(
        self, marketplace: MarketplaceVersions
    ) -> Tuple[Dict, Dict]:
        """
        Gets the pack content items and display names to add into the pack's metadata dictionary.
        For each content item the function generates its `summary` and calculating the from/to version
        on whether to add this item to the content items list.

        Args:
            marketplace (MarketplaceVersions): The marketplace to which the pack should belong to.

        Returns:
            Tuple[Dict, Dict]: The content items and display names dictionaries to add to the pack metadata.
        """
        content_items: dict = {}
        content_displays: dict = {}
        for content_item in self.content_items:

            if content_item.content_type == ContentType.TEST_PLAYBOOK:
                logger.debug(
                    f"Skip loading the {content_item.name} test playbook into metadata.json"
                )
                continue

            add_item_to_metadata_list(
                collected_content_items=content_items,
                content_item=content_item,
                marketplace=marketplace,
            )

            content_displays[
                content_item.content_type.metadata_name
            ] = content_item.content_type.metadata_display_name

        content_displays = {
            content_type: content_type_display
            if (content_items[content_type] and len(content_items[content_type]) == 1)
            else f"{content_type_display}s"
            for content_type, content_type_display in content_displays.items()
        }

        return content_items, content_displays

    def enhance_dependencies(self, marketplace):
        """
        Gathers the first level pack's dependencies details to a list to add to the pack's metadata.
        For each dependency it adds the following pack's properties:
        `mandatory`, `minVersion`, `author`, `name`, `certification`

        Args:
            marketplace (MarketplaceVersions): The marketplace to which the pack should belong to.

        Returns:
            dict: The dependencies of the pack.
        """
        return {
            r.content_item_to.object_id: {
                "mandatory": r.mandatorily,
                "minVersion": r.content_item_to.current_version,  # type:ignore[attr-defined]
                "author": r.content_item_to.author  # type:ignore[attr-defined]
                if marketplace == MarketplaceVersions.XSOAR
                else r.content_item_to.author.replace(  # type:ignore[attr-defined]
                    "XSOAR", "XSIAM"
                ),
                "name": r.content_item_to.name,  # type:ignore[attr-defined]
                "certification": r.content_item_to.certification  # type:ignore[attr-defined]
                or "",
            }
            for r in self.depends_on
            if r.is_direct
        }

    def get_pack_tags(self, marketplace) -> list:
        """
        Gets the pack's tags considering the pack content item's properties.
        For example, if the pack has a script which is a transformer or a filter,
        then the pack will have the tags "Transformer" or "Filter" accordingly.

        Args:
            marketplace (MarketplaceVersions): The marketplace to which the pack should belong to.

        Returns:
            list: The list of tags to add to the pack's metadata.
        """
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

    def is_data_source(self) -> bool:
        """Returns a boolean result on whether the pack should considered as a "Data Source" pack."""
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


def add_item_to_metadata_list(
    collected_content_items: dict,
    content_item: ContentItem,
    marketplace: MarketplaceVersions,
    incident_to_alert: bool = False,
):
    """
    Adds the given content item to the metadata content items list.
    - Checks if the given content item was already added to the metadata content items list
      and replaces the object if its `toversion` is higher than the existing metadata object's `toversion`.
    - If the content item name should be replaced from incident to alert, then the function will be called recursively
      to replace also the item that its name was replaced from incident to alert.

    Args:
        collected_content_items (dict): The content items metadata list that were already collected.
        content_item (ContentItem): The current content item to check.
        marketplace (MarketplaceVersions): The marketplace to prepare the pack to upload.
        incident_to_alert (bool, optional): Whether should replace incident to alert. Defaults to False.
    """
    collected_content_items.setdefault(content_item.content_type.metadata_name, [])
    content_item_summary = content_item.summary(
        marketplace, incident_to_alert=incident_to_alert
    )

    if content_item_metadata := search_content_item_metadata_object(
        collected_content_items=collected_content_items,
        item_id=content_item_summary["id"],
        item_name=content_item_summary["name"],
        item_type_key=content_item.content_type.metadata_name,
    ):
        content_item_metadata = content_item_metadata[0]
        logger.debug(
            f'Found content item with name "{content_item.name}" that was already appended to the list'
        )

        replace_item_if_has_higher_toversion(
            content_item, content_item_metadata, content_item_summary
        )

    else:
        logger.debug(
            f'Didn\'t find content item with name "{content_item.name}" in the list, appending.'
        )
        set_empty_toversion_if_default(content_item_summary)
        collected_content_items[content_item.content_type.metadata_name].append(
            content_item_summary
        )

    # If incident_to_alert is True then stop recursive
    if not incident_to_alert and content_item.is_incident_to_alert(marketplace):
        logger.debug(
            f'Replacing incident to alert in content item with ID "{content_item.object_id}" and appending to metadata'
        )
        add_item_to_metadata_list(
            collected_content_items, content_item, marketplace, incident_to_alert=True
        )


def replace_item_if_has_higher_toversion(
    content_item: ContentItem, content_item_metadata: dict, content_item_summary: dict
):
    """
    Replaces the content item metadata object in the content items metadata list
    if the given content item's `toversion` is higher than the existing item's metadata `toversion`.

    Args:
        content_item (ContentItem): The current content item to check.
        content_item_metadata (dict): The existing content item metadata object in the list.
        content_item_summary (dict): The current content item summary to update if needed.
    """
    if parse(content_item.toversion) > parse(
        content_item_metadata["toversion"] or DEFAULT_CONTENT_ITEM_TO_VERSION
    ):
        logger.debug(
            f'Current content item with name "{content_item.name}" has higher `toversion` than the existing object, '
            "updating its metadata."
        )
        content_item_metadata.update(content_item_summary.items())
        set_empty_toversion_if_default(content_item_metadata)


def set_empty_toversion_if_default(content_item_dict: dict):
    """
    Sets the content item's `toversion` value to empty if it's the default value.

    Args:
        content_item_dict (dict): The content item object to set.
    """
    content_item_dict["toversion"] = (
        content_item_dict["toversion"]
        if content_item_dict["toversion"] != DEFAULT_CONTENT_ITEM_TO_VERSION
        else ""
    )


def search_content_item_metadata_object(
    collected_content_items: dict,
    item_id: Optional[str],
    item_name: Optional[str],
    item_type_key: Optional[str],
):
    """
    Search an content item object in the content items metadata list by its ID and name.

    Args:
        collected_content_items (dict): The content items metadata list that were already collected.
        item_id (Optional[str]): The content item ID to search.
        item_name (Optional[str]): The content item name to search.
        item_type_key (Optional[str]): The content item type key to search in its list value that exists in the collected_content_items dict.

    Returns:
        list: List of the found content items.
    """
    return [
        content_item
        for content_item in collected_content_items[item_type_key]
        if content_item.get("id") == item_id and content_item.get("name") == item_name
    ]
