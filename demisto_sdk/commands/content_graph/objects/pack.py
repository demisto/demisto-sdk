import shutil
from collections import defaultdict
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Callable, Optional

import demisto_client
from demisto_client.demisto_api.rest import ApiException
from packaging.version import Version, parse
from pydantic import DirectoryPath, Field, validator

from demisto_sdk.commands.common.constants import (
    BASE_PACK,
    CONTRIBUTORS_README_TEMPLATE,
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    MARKETPLACE_MIN_VERSION,
    ImagesFolderNames,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.tools import MarketplaceTagParser
from demisto_sdk.commands.content_graph.common import (
    PACK_METADATA_FILENAME,
    ContentType,
    Nodes,
    Relationships,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    NotIndivitudallyUploadableException,
)
from demisto_sdk.commands.content_graph.objects.exceptions import (
    FailedUploadException,
    FailedUploadMultipleException,
)
from demisto_sdk.commands.content_graph.objects.pack_content_items import (
    PackContentItems,
)
from demisto_sdk.commands.content_graph.objects.pack_metadata import PackMetadata
from demisto_sdk.commands.prepare_content.markdown_images_handler import (
    replace_markdown_urls_and_upload_to_artifacts,
)
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

import tempfile
from configparser import ConfigParser, MissingSectionHeaderError
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import List, Set

from demisto_sdk.commands.common.constants import PACKS_PACK_IGNORE_FILE_NAME
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_remote_file_from_api

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


class PackIgnore(dict):
    class Section(str, Enum):
        KNOWN_WORDS = "known_words"
        TESTS_REQUIRE_NETWORK = "tests_require_network"
        FILE = "file:"
        IGNORE = "ignore"

    def __init__(self, content: ConfigParser, path: Path, *args, **kwargs):
        self._content = content
        self._path = path
        super().__init__(*args, **kwargs)

    @classmethod
    @lru_cache
    def __load(cls, pack_ignore_path: Path) -> "PackIgnore":
        """
        Load the .pack-ignore file into a ConfigParser from a given path
        """
        if pack_ignore_path.exists():
            try:
                config = ConfigParser(allow_no_value=True)
                config.read(pack_ignore_path)
                return cls(content=config, path=pack_ignore_path)
            except MissingSectionHeaderError:
                logger.error(
                    f"Error when retrieving the content of .pack-ignore in path {pack_ignore_path}"
                )
                raise
        logger.warning(
            f"[red]Could not find .pack-ignore file at path {pack_ignore_path}[/red]"
        )
        raise FileNotFoundError(
            f"Could not find the .pack-ignore path at {pack_ignore_path}"
        )

    def __map_files_to_ignored_validations(self):
        for section in filter(
            lambda _section: _section.startswith(self.Section.FILE), self._content.sections()
        ):
            self.add(
                section,
                self._content[section],
                lambda x: set(x[self.Section.IGNORE].strip().split(","))
                if self.Section.IGNORE in x
                else set(),
            )

    @classmethod
    def from_path(cls, path: Path) -> "PackIgnore":
        """
        init the PackIgnore from a local file path.

        Args:
            path (Path): path of the pack.
        """
        return cls.__load(CONTENT_PATH / path / PACKS_PACK_IGNORE_FILE_NAME)

    @classmethod
    @lru_cache
    def from_remote_path(cls, remote_path: str, tag: str = "master") -> "PackIgnore":
        """
        init the PackIgnore from a remote file path.

        Args:
            remote_path (path): remote file path.
            tag (str): the branch/commit to retrieve the file content.
        """
        pack_ignore_file_content: bytes = (
            get_remote_file_from_api(remote_path, tag=tag, return_content=True) or b""  # type: ignore[assignment]
        )

        with tempfile.NamedTemporaryFile(
            prefix=f'{remote_path.replace("/", "_")}:{tag}-'
        ) as pack_ignore_path:
            pack_ignore_path.write(pack_ignore_file_content)
            pack_ignore = cls.__load(Path(pack_ignore_path.name))

        pack_ignore.__map_files_to_ignored_validations()
        return pack_ignore

    def add(self, key: str, section: Any, cast_func: Callable = lambda x: x) -> None:
        self.__setitem__(key, cast_func(section))

    def get(self, key: str, default: Any = None, cast_func: Callable = lambda x: x) -> Any:
        """
        Get a section from the .pack-ignore, in case key does not exist, will add it for caching purposes

        Args:
            key (str): the key to add.
            default (Any): in case any default value is needed
            cast_func (Callable): cast to any type when adding the key
        """
        if self._content.has_section(key):
            section = self._content[key]
            if not super().get(key):
                self.add(key, section, cast_func)
            return super().get(key)

        return default

    @property
    def path(self) -> Path:
        return self._path

    @property
    def known_words(self) -> Set[str]:
        """
        Returns a list of all the known words within the .pack-ignore
        """
        return self.get(
            self.Section.KNOWN_WORDS, default=set(), cast_func=lambda x: set(x)
        )

    @property
    def script_integration_ids_tests_require_docker_network(self) -> Set[str]:
        """
        Returns a list of all the scripts/integration IDs within a pack that requires docker network for unit-testing.
        """
        return self.get(
            self.Section.TESTS_REQUIRE_NETWORK,
            default=set(),
            cast_func=lambda x: set(x),
        )

    def get_ignored_validations_by_file_name(self, file_name: str) -> Set:
        """
        Get the ignored validations of a file within the .pack-ignore if exist

        Args:
            file_name (str): file name to retrieve its ignored validations
        """
        return self.get(
            f"{self.Section.FILE}{file_name}",
            default=set(),
            cast_func=lambda x: set(x[self.Section.IGNORE].strip().split(","))
            if self.Section.IGNORE in x
            else set(),
        )

    def get_ignored_validations_by_file_names(self, file_names: List[str]) -> Set[str]:
        """
        Get the ignored validations of a list of files within the .pack-ignore if exist

        Args:
            file_names (List[str]): file names to retrieve their ignored validations
        """
        ignored_validations: Set[str] = set()

        for file_name in file_names:
            ignored_validations.union(
                self.get_ignored_validations_by_file_name(file_name)
            )

        return ignored_validations


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
    def pack_ignore(self) -> Optional[PackIgnore]:
        try:
            return PackIgnore.from_path(self.path)
        except (FileNotFoundError, MissingSectionHeaderError) as error:
            logger.debug(
                f"Error when trying to get .pack-ignore of pack {self.object_id}: {error}"
            )
            return None

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
                min(
                    [
                        parse(content_item.fromversion)
                        for content_item in content_items
                        if not content_item.is_test
                        and content_item.fromversion
                        != DEFAULT_CONTENT_ITEM_FROM_VERSION
                    ],
                    default=MARKETPLACE_MIN_VERSION,
                )
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
        self._enhance_pack_properties(marketplace, self.object_id, self.content_items)

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
        metadata.update(
            self._format_metadata(marketplace, self.content_items, self.depends_on)
        )

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

                if (
                    marketplace == MarketplaceVersions.XSOAR
                    and MarketplaceVersions.XSOAR_ON_PREM in self.marketplaces
                ):
                    marketplace = MarketplaceVersions.XSOAR_ON_PREM
                parsed_text = MarketplaceTagParser(marketplace).parse_text(text)
                if len(text) != len(parsed_text):
                    f.seek(0)
                    f.write(parsed_text)
                    f.truncate()
            except Exception as e:
                logger.error(f"Failed dumping readme: {e}")

        replace_markdown_urls_and_upload_to_artifacts(
            path, marketplace, self.object_id, file_type=ImagesFolderNames.README_IMAGES
        )

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
