from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set

import pydantic
import regex
from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.constants import (
    BASE_PACK,
    DEFAULT_SUPPORTED_MODULES,
    DEPRECATED_DESC_REGEX,
    DEPRECATED_NO_REPLACE_DESC_REGEX,
    PACK_DEFAULT_MARKETPLACES,
    PACK_NAME_DEPRECATED_REGEX,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    capital_case,
    get_file,
    get_json,
    get_pack_ignore_content,
    get_pack_latest_rn_version,
)
from demisto_sdk.commands.content_graph.common import (
    PACK_CONTRIBUTORS_FILENAME,
    PACK_METADATA_FILENAME,
    ContentType,
    Relationships,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser
from demisto_sdk.commands.content_graph.parsers.content_item import (
    ContentItemParser,
    InvalidContentItemException,
    NotAContentItemException,
)
from demisto_sdk.commands.content_graph.parsers.content_items_list import (
    ContentItemsList,
)
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StructureError,
)
from demisto_sdk.commands.content_graph.strict_objects.pack_meta_data import (
    StrictPackMetadata,
)
from demisto_sdk.commands.content_graph.strict_objects.release_notes_config import (
    StrictReleaseNotesConfig,
)


class PackContentItems:
    """A class that holds all pack's content items in lists by their types."""

    def __init__(self) -> None:
        self.case_field = ContentItemsList(content_type=ContentType.CASE_FIELD)
        self.case_layout = ContentItemsList(content_type=ContentType.CASE_LAYOUT)
        self.case_layout_rule = ContentItemsList(
            content_type=ContentType.CASE_LAYOUT_RULE
        )
        self.classifier = ContentItemsList(content_type=ContentType.CLASSIFIER)
        self.correlation_rule = ContentItemsList(
            content_type=ContentType.CORRELATION_RULE
        )
        self.dashboard = ContentItemsList(content_type=ContentType.DASHBOARD)
        self.generic_definition = ContentItemsList(
            content_type=ContentType.GENERIC_DEFINITION
        )
        self.generic_field = ContentItemsList(content_type=ContentType.GENERIC_FIELD)
        self.generic_module = ContentItemsList(content_type=ContentType.GENERIC_MODULE)
        self.generic_type = ContentItemsList(content_type=ContentType.GENERIC_TYPE)
        self.incident_field = ContentItemsList(content_type=ContentType.INCIDENT_FIELD)
        self.incident_type = ContentItemsList(content_type=ContentType.INCIDENT_TYPE)
        self.indicator_field = ContentItemsList(
            content_type=ContentType.INDICATOR_FIELD
        )
        self.indicator_type = ContentItemsList(content_type=ContentType.INDICATOR_TYPE)
        self.integration = ContentItemsList(content_type=ContentType.INTEGRATION)
        self.job = ContentItemsList(content_type=ContentType.JOB)
        self.layout = ContentItemsList(content_type=ContentType.LAYOUT)
        self.list = ContentItemsList(content_type=ContentType.LIST)
        self.mapper = ContentItemsList(content_type=ContentType.MAPPER)
        self.modeling_rule = ContentItemsList(content_type=ContentType.MODELING_RULE)
        self.parsing_rule = ContentItemsList(content_type=ContentType.PARSING_RULE)
        self.playbook = ContentItemsList(content_type=ContentType.PLAYBOOK)
        self.report = ContentItemsList(content_type=ContentType.REPORT)
        self.script = ContentItemsList(content_type=ContentType.SCRIPT)
        self.test_playbook = ContentItemsList(content_type=ContentType.TEST_PLAYBOOK)
        self.trigger = ContentItemsList(content_type=ContentType.TRIGGER)
        self.widget = ContentItemsList(content_type=ContentType.WIDGET)
        self.wizard = ContentItemsList(content_type=ContentType.WIZARD)
        self.xsiam_dashboard = ContentItemsList(
            content_type=ContentType.XSIAM_DASHBOARD
        )
        self.xsiam_report = ContentItemsList(content_type=ContentType.XSIAM_REPORT)
        self.xdrc_template = ContentItemsList(content_type=ContentType.XDRC_TEMPLATE)
        self.layout_rule = ContentItemsList(content_type=ContentType.LAYOUT_RULE)
        self.preprocess_rule = ContentItemsList(
            content_type=ContentType.PREPROCESS_RULE
        )
        self.test_script = ContentItemsList(content_type=ContentType.TEST_SCRIPT)
        self.assets_modeling_rule = ContentItemsList(
            content_type=ContentType.ASSETS_MODELING_RULE
        )

    def iter_lists(self) -> Iterator[ContentItemsList]:
        yield from vars(self).values()

    def append(self, obj: ContentItemParser) -> None:
        """
        Appends the object to the list with the same content_type.

        Args:
            obj (ContentItemParser): The content item to append.

        Raises:
            NotAContentItemException: If did not find any matching content item list.
        """
        for item_list in self.iter_lists():
            if item_list.content_type == obj.content_type:
                item_list.append(obj)
                return

        raise NotAContentItemException(
            f"Could not find list of {obj.content_type} items"
        )


NOW = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")


class PackMetadataParser:
    """A pack metadata parser."""

    def __init__(self, path: Path, metadata: Dict[str, Any]) -> None:
        self._metadata: Dict[str, Any] = metadata
        self.name: str = metadata.get("name", "")
        self.display_name: str = metadata.get("name", "")
        self.description: str = metadata.get("description", "")
        self.support: str = metadata.get("support", "")
        self.created: str = metadata.get("created") or NOW
        self.updated: str = metadata.get("updated") or NOW
        self.legacy: bool = metadata.get(
            "legacy", metadata.get("partnerId") is None
        )  # default: True, private default: False
        self.email: str = metadata.get("email") or ""
        self.eulaLink: str = (
            metadata.get("eulaLink")
            or "https://github.com/demisto/content/blob/master/LICENSE"
        )
        self.author_image: str = self.get_author_image_filepath(path=path)
        self.price: int = int(metadata.get("price") or 0)
        self.hidden: bool = metadata.get("hidden", False)
        self.server_min_version: str = metadata.get("serverMinVersion", "")
        self.current_version: str = metadata.get("currentVersion", "")
        self.version_info: str = ""
        try:
            self.commit: str = GitUtil().get_current_commit_hash() or ""
        except InvalidGitRepositoryError as e:
            logger.warning(
                f"Failed to get commit hash for pack {self.name}. Error: {e}"
            )
            self.commit = ""
        self.downloads: int = 0
        self.tags: List[str] = metadata.get("tags") or []
        self.default_data_source_id: str = metadata.get("defaultDataSource") or ""
        self.keywords: List[str] = metadata.get("keywords", [])
        self.search_rank: int = 0
        self.videos: List[str] = metadata.get("videos", [])
        self.excluded_dependencies: List[str] = metadata.get("excludedDependencies", [])
        self.modules: List[str] = metadata.get("modules", [])
        self.integrations: List[str] = []

        # For private packs
        self.premium: Optional[bool] = "partnerId" in metadata
        self.vendor_id: Optional[str] = metadata.get("vendorId") or ""
        self.partner_id: Optional[str] = metadata.get("partnerId") or ""
        self.partner_name: Optional[str] = metadata.get("partnerName") or ""
        self.preview_only: Optional[bool] = metadata.get("previewOnly") or False
        self.disable_monthly: Optional[bool] = metadata.get("disableMonthly") or False
        self.content_commit_hash: Optional[str] = (
            metadata.get("contentCommitHash") or ""
        )
        self.hybrid: bool = metadata.get("hybrid") or False
        self.pack_metadata_dict: dict = metadata
        self.supportedModules: List[str] = metadata.get(
            "supportedModules", DEFAULT_SUPPORTED_MODULES
        )

    @property
    def url(self) -> str:
        if "url" in self.pack_metadata_dict and self.pack_metadata_dict["url"]:
            return self.pack_metadata_dict.get("url", "")
        return (
            "https://www.paloaltonetworks.com/cortex" if self.support == "xsoar" else ""
        )

    @property
    def certification(self):
        if self.support in ["xsoar", "partner"]:
            return "certified"
        return self.pack_metadata_dict.get("certification") or ""

    @property
    def author(self):
        return (
            self.pack_metadata_dict.get(
                "author", "Cortex XSOAR" if self.support == "xsoar" else ""
            )
            or ""
        )

    @property
    def categories(self):
        return [capital_case(c) for c in self.pack_metadata_dict.get("categories", [])]

    @property
    def use_cases(self):
        return [capital_case(c) for c in self.pack_metadata_dict.get("useCases", [])]

    @property
    def marketplaces(self) -> List[MarketplaceVersions]:
        marketplaces = self._metadata.get("marketplaces") or PACK_DEFAULT_MARKETPLACES
        marketplace_set: Set[MarketplaceVersions] = (
            BaseContentParser.update_marketplaces_set_with_xsoar_values(
                {MarketplaceVersions(mp) for mp in marketplaces}
            )
        )
        return sorted(list(marketplace_set))

    def get_author_image_filepath(self, path: Path) -> str:
        if (path / "Author_image.png").is_file():
            return f"content/packs/{path.name}/Author_image.png"
        elif self.support == "xsoar":
            return "content/packs/Base/Author_image.png"
        return ""


class PackParser(BaseContentParser, PackMetadataParser):
    """A parsed representation of a pack.

    Attributes:
        marketplaces (List[MarketplaceVersions]): The marketplaces supporting this pack.
        content_items (PackContentItems): A collection of this pack's content item parsers.
        relationships (Relationships): A collection of the relationships in this pack.
    """

    content_type = ContentType.PACK

    def __init__(
        self, path: Path, git_sha: Optional[str] = None, metadata_only: bool = False
    ) -> None:
        """Parses a pack and its content items.

        Args:
            path (Path): The pack path.
        """
        if path.name == PACK_METADATA_FILENAME:
            path = path.parent
        BaseContentParser.__init__(self, path)
        self.structure_errors: List[StructureError] = self.validate_structure()

        try:
            metadata = get_json(path / PACK_METADATA_FILENAME, git_sha=git_sha)
            if not metadata or not isinstance(metadata, dict):
                raise NotAContentItemException(
                    f"Please make sure that the {PACK_METADATA_FILENAME} is a non-empty dict for pack {path=}"
                )
        except FileNotFoundError:
            raise NotAContentItemException(
                f"{PACK_METADATA_FILENAME} not found in pack in {path=}.\nPlease make sure the file exists and is a valid json file."
            )
        except OSError:
            raise NotAContentItemException(
                f"{PACK_METADATA_FILENAME} in {path=} couldn't be open."
            )

        PackMetadataParser.__init__(self, path, metadata)

        self.content_items: PackContentItems = PackContentItems()
        self.relationships: Relationships = Relationships()
        self.connect_pack_dependencies(metadata)
        try:
            self.contributors: List[str] = (
                get_json(path / PACK_CONTRIBUTORS_FILENAME, git_sha=git_sha) or []
            )
        except FileNotFoundError:
            logger.debug(f"No contributors file found in {path}")
        logger.debug(f"Parsing {self.node_id}")
        self.parse_ignored_errors()
        if not metadata_only:
            self.parse_pack_folders()
        self.get_rn_info(git_sha)

        logger.debug(f"Successfully parsed {self.node_id}")

    @property
    def object_id(self) -> Optional[str]:
        return self.path.name

    def connect_pack_dependencies(self, metadata: Dict[str, Any]) -> None:
        dependency: Dict[str, Dict[str, Any]]
        try:
            for pack_id, dependency in metadata.get("dependencies", {}).items():
                self.relationships.add(
                    RelationshipType.DEPENDS_ON,
                    source=self.object_id,
                    target=pack_id,
                    mandatorily=dependency.get("mandatory"),
                    target_min_version=dependency.get("minVersion"),
                )
        except AttributeError as error:
            raise AttributeError(
                f"Couldn't parse dependencies section for pack {self.name} pack_metadata. Dependencies section must be a valid dictionary."
            ) from error

        if (
            self.object_id != BASE_PACK
        ):  # add Base pack dependency for all the packs except Base itself
            self.relationships.add(
                RelationshipType.DEPENDS_ON,
                source=self.object_id,
                target=BASE_PACK,
                mandatorily=True,
            )

    def parse_pack_folders(self) -> None:
        """Parses all pack content items by iterating its folders."""
        for folder_path in ContentType.pack_folders(self.path):
            for (
                content_item_path
            ) in folder_path.iterdir():  # todo: consider multiprocessing
                self.parse_content_item(content_item_path)

    def parse_content_item(self, content_item_path: Path) -> None:
        """Potentially parses a single content item.

        Args:
            content_item_path (Path): The content item path.
        """
        try:
            content_item = ContentItemParser.from_path(
                content_item_path, self.marketplaces, self.supportedModules
            )
            content_item.add_to_pack(self.object_id)
            self.content_items.append(content_item)
            self.relationships.update(content_item.relationships)
        except NotAContentItemException:
            logger.debug(f"Skipping {content_item_path} - not a content item")
        except InvalidContentItemException:
            logger.error(f"{content_item_path} - invalid content item")
            raise

    @property
    def deprecated(self) -> bool:
        if regex.match(PACK_NAME_DEPRECATED_REGEX, self.name) and (
            regex.match(DEPRECATED_NO_REPLACE_DESC_REGEX, self.description)
            or regex.match(DEPRECATED_DESC_REGEX, self.description)
        ):
            return True
        return False

    def parse_ignored_errors(self):
        """Sets the pack's ignored_errors field."""
        try:
            self.ignored_errors_dict = (
                dict(get_pack_ignore_content(self.path.name) or {})  # type:ignore[var-annotated]
            )
        except Exception as e:
            logger.warning(
                f"Failed to extract ignored errors list for {self.path.name} for {self.object_id}, reason: {e}"
            )

    def get_rn_info(self, git_sha: Optional[str] = None):
        self.latest_rn_version = get_pack_latest_rn_version(str(self.path), git_sha)

    @cached_property
    def field_mapping(self):
        return {
            "name": "name",
            "description": "description",
            "created": "created",
            "support": "support",
            "email": "email",
            "price": "price",
            "hidden": "hidden",
            "server_min_version": "serverMinVersion",
            "current_version": "currentVersion",
            "tags": "tags",
            "keywords": "keywords",
            "videos": "videos",
            "marketplaces": "marketplaces",
            "vendor_id": "vendorId",
            "partner_id": "partnerId",
            "partner_name": "partnerName",
            "preview_only": "previewOnly",
            "excluded_dependencies": "excludedDependencies",
            "modules": "modules",
            "disable_monthly": "disableMonthly",
            "content_commit_hash": "contentCommitHash",
            "default_data_source_id": "defaultDataSource",
        }

    def raw_data(self) -> dict:
        raise NotImplementedError

    @property
    def strict_object(self):
        raise NotImplementedError("This object has a different behavior")

    def validate_structure(self) -> List[StructureError]:
        """
        This method uses the parsed data and attempts to build a Pydantic (strict) object from it.
        Whenever the data and schema mismatch, we store the error using the 'structure_errors' attribute,
        which will be read during the ST110 validation run.
        In Pack, we need to check two files: the metadata and the RNs json files, so we override the
        method for combing all the pydantic errors from the both files.
        """
        pydantic_error_list: List[StructureError] = []

        # validate Rn's files
        for file in self.path.glob("ReleaseNotes/*.json"):
            validate_structure(file, pydantic_error_list)

        # validate pack metadata file
        validate_structure(
            Path(self.path, PACK_METADATA_FILENAME),
            pydantic_error_list,
        )

        return pydantic_error_list


def validate_structure(file: Path, pydantic_error_list: list) -> None:
    """
    This function is called by the method validate_structure and build the appropriate strict object.
    In case of invalid structure file, adds the error to the given list.
    """
    try:
        if file.stem == "pack_metadata":
            StrictPackMetadata.parse_obj(get_file(file))
        else:
            StrictReleaseNotesConfig.parse_obj(get_file(file))
    except pydantic.error_wrappers.ValidationError as e:
        pydantic_error_list += [
            StructureError(path=file, **error) for error in e.errors()
        ]
