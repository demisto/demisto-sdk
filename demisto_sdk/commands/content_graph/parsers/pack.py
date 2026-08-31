from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set

import pydantic
import regex
from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.constants import (
    AGENTIX_ACTIONS_DIR,
    BASE_PACK,
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
    DERIVED_PACK_ALLOWED_SUPPORT_LEVELS,
    DERIVED_PACK_SUFFIX,
    ENABLE_SPLIT_PACKS,
    PACK_CONTRIBUTORS_FILENAME,
    PACK_METADATA_FILENAME,
    ContentType,
    Relationships,
    RelationshipType,
    derived_pack_exclusions,
    is_deprecated_content_item,
    is_deprecated_pack,
    resolve_derived_pack_source,
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
        self.agentix_action = ContentItemsList(content_type=ContentType.AGENTIX_ACTION)
        self.agentix_action_test = ContentItemsList(
            content_type=ContentType.AGENTIX_ACTION_TEST
        )
        self.agentix_agent = ContentItemsList(content_type=ContentType.AGENTIX_AGENT)
        self.agentix_skill = ContentItemsList(content_type=ContentType.AGENTIX_SKILL)
        self.collection = ContentItemsList(content_type=ContentType.COLLECTION)

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
        self.created = metadata.get("firstCreated") or metadata.get("created")
        if not self.created:
            try:
                self.created = GitUtil(path).get_file_creation_date(file_path=path)
            except InvalidGitRepositoryError:
                logger.debug(
                    f"Could not find git repository for {path}, using current time as creation time."
                )
                self.created = NOW
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
            self.commit: str = GitUtil(path).get_current_commit_hash() or ""
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
        self.supportedModules: Optional[List[str]] = metadata.get("supportedModules")
        self.source: str = metadata.get("source", "")
        self.managed: bool = metadata.get("managed", False)
        self.internal: bool = metadata.get("internal", False)
        self.coupling_overrides: Optional[Dict[str, str]] = metadata.get(
            "coupling_overrides"
        )
        # Per-pack override for the feature name this pack's derived twin is
        # published under. Highest-precedence input to
        # resolve_derived_pack_source().
        self.derived_source: Optional[str] = metadata.get("derived_source")

        # Marketplace-suffixed managed/source fields (not private-pack specific).
        # Kept as-is here; they are resolved into the plain managed/source
        # per-marketplace during dump
        # (see MarketplaceSuffixPreparer.prepare_managed_and_source).
        self.managed_platform: Optional[bool] = metadata.get("managed:platform")
        self.source_platform: Optional[str] = metadata.get("source:platform")

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

    @staticmethod
    def resolve_marketplaces(
        metadata: Dict[str, Any],
    ) -> List[MarketplaceVersions]:
        """Resolve the pack's marketplaces from a metadata dict, applying the
        default marketplaces and the xsoar value normalization."""
        marketplaces = metadata.get("marketplaces") or PACK_DEFAULT_MARKETPLACES
        marketplace_set: Set[MarketplaceVersions] = (
            BaseContentParser.update_marketplaces_set_with_xsoar_values(
                {MarketplaceVersions(mp) for mp in marketplaces}
            )
        )
        return sorted(list(marketplace_set))

    @property
    def marketplaces(self) -> List[MarketplaceVersions]:
        return self.resolve_marketplaces(self._metadata)

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
        self,
        path: Path,
        git_sha: Optional[str] = None,
        metadata_only: bool = False,
        private_pack_path: Optional[Path] = None,
    ) -> None:
        """Parses a pack and its content items.

        Args:
            path (Path): The pack path.
        """
        if path.name == PACK_METADATA_FILENAME:
            path = path.parent
        BaseContentParser.__init__(self, path)
        self.private_pack_path = private_pack_path
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

        # Generate derived pack for split-pack candidates (feature-flagged)
        self.derived_pack: Optional["DerivedPackParser"] = None
        if ENABLE_SPLIT_PACKS and not metadata_only:
            self.derived_pack = self._generate_derived_pack()

        logger.debug(f"Successfully parsed {self.node_id}")

    @property
    def object_id(self) -> Optional[str]:
        return self.path.name

    def _is_item_tightly_coupled(self, content_item: "ContentItemParser") -> bool:
        """Check if a content item is tightly coupled, respecting overrides.

        A deprecated item is never tightly coupled: it must not be carried into a
        derived pack even when an explicit override says otherwise, so the
        deprecation check deliberately precedes ``coupling_overrides``.

        Kept in sync with ``Pack._is_item_tightly_coupled``
        (``objects/pack.py``), which mirrors this rule on the object side.
        """
        if is_deprecated_content_item(content_item):
            return False
        overrides = self.coupling_overrides or {}
        item_id = content_item.object_id
        if item_id and item_id in overrides:
            return overrides[item_id] == "tightly_coupled"
        return content_item.content_type.is_tightly_coupled

    def _is_derived_pack_eligible(self) -> bool:
        """Whether this pack may yield a derived (split) pack at all.

        Checked before any content is inspected. A pack is ineligible when any of
        the following holds:
            - it is already ``managed`` (managed packs are never split);
            - its ``support`` level is not in
              ``DERIVED_PACK_ALLOWED_SUPPORT_LEVELS`` (only xsoar-supported packs
              qualify; a missing or empty support level is not xsoar);
            - it is deprecated;
            - it is ``hidden``;
            - its pack id appears in the ``DERIVED_PACKS_EXCLUDE`` environment
              variable.

        Returns:
            True if the pack may yield a derived pack, False otherwise.
        """
        pack_id = self.object_id or ""
        if self.managed:
            logger.debug(
                f"Pack '{pack_id}' is not derived-pack eligible: it is already managed"
            )
            return False
        if (self.support or "").casefold() not in DERIVED_PACK_ALLOWED_SUPPORT_LEVELS:
            logger.debug(
                f"Pack '{pack_id}' is not derived-pack eligible: support level "
                f"'{self.support}' is not one of {sorted(DERIVED_PACK_ALLOWED_SUPPORT_LEVELS)}"
            )
            return False
        if is_deprecated_pack(self):
            logger.debug(
                f"Pack '{pack_id}' is not derived-pack eligible: the pack is deprecated"
            )
            return False
        if self.hidden:
            logger.debug(
                f"Pack '{pack_id}' is not derived-pack eligible: the pack is hidden"
            )
            return False
        if pack_id.casefold() in derived_pack_exclusions():
            logger.debug(
                f"Pack '{pack_id}' is not derived-pack eligible: it is listed in the exclusion list"
            )
            return False
        return True

    def _has_eligible_integration(self) -> bool:
        """Whether the pack holds at least one integration fit for a derived pack.

        An integration qualifies under the very same filtering applied to every
        content item carried into the derived pack, i.e.
        ``_is_item_tightly_coupled`` (which excludes deprecated integrations and
        honors ``coupling_overrides``).

        Returns:
            True if at least one integration qualifies, False otherwise.
        """
        return any(
            item.content_type == ContentType.INTEGRATION
            and self._is_item_tightly_coupled(item)
            for item_list in self.content_items.iter_lists()
            for item in item_list
        )

    def _generate_derived_pack(self) -> Optional["DerivedPackParser"]:
        """Generate a derived pack for split-pack candidates.

        A pack is a split-pack candidate when:
        - It is eligible per ``_is_derived_pack_eligible``: not ``managed``,
          xsoar-supported, not deprecated, not ``hidden``, and not listed in the
          ``DERIVED_PACKS_EXCLUDE`` environment variable
        - It holds at least one qualifying integration per
          ``_has_eligible_integration``
        - It contains at least one tightly coupled content item that is not
          deprecated (respecting ``coupling_overrides``)

        Returns:
            A ``DerivedPackParser`` if the pack qualifies, otherwise ``None``.
        """
        if not self._is_derived_pack_eligible():
            return None

        if not self._has_eligible_integration():
            logger.debug(
                f"Pack '{self.object_id}' yields no derived pack: "
                "it has no eligible integration"
            )
            return None

        tightly_coupled_items = [
            item
            for item_list in self.content_items.iter_lists()
            for item in item_list
            if self._is_item_tightly_coupled(item)
        ]

        if not tightly_coupled_items:
            return None

        derived_id = f"{self.object_id}{DERIVED_PACK_SUFFIX}"
        logger.debug(
            f"Generating derived pack '{derived_id}' from '{self.object_id}' "
            f"with {len(tightly_coupled_items)} tightly coupled items"
        )

        derived = DerivedPackParser(
            original_parser=self,
            derived_id=derived_id,
        )

        # Add second IN_PACK edge for each tightly coupled item
        for item in tightly_coupled_items:
            item.add_to_pack(derived_id)
            derived.relationships.update(item.relationships)

        return derived

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
            is_agentix_actions_folder = folder_path.name == AGENTIX_ACTIONS_DIR
            for (
                content_item_path
            ) in folder_path.iterdir():  # todo: consider multiprocessing
                # Skip test_data directories (old test file structure)
                if content_item_path.name == "test_data":
                    continue
                self.parse_content_item(content_item_path)

                # For AgentixActions directories, also parse test files
                # inside the action subdirectory as separate content items.
                if is_agentix_actions_folder and content_item_path.is_dir():
                    for file in content_item_path.iterdir():
                        if file.suffix in (
                            ".yml",
                            ".yaml",
                        ) and file.stem.endswith("_test"):
                            self.parse_content_item(file)
        if self.private_pack_path:
            self.parse_content_test_conf_folders()

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

    def parse_content_test_conf_folders(self):
        logger.info("Checking if content-test-conf repo has additional content items.")
        if self.private_pack_path and self.private_pack_path.is_dir():
            logger.info(f"{str(self.private_pack_path)} is a dir.")
            for folder_path in ContentType.pack_folders(self.private_pack_path):
                for content_item_path in folder_path.iterdir():
                    self.parse_content_item(content_item_path)
        else:
            logger.info(
                "Can not find the pack under content-test-conf-repo, prepare-content only using content repo."
            )

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
            self.ignored_errors_dict = dict(
                get_pack_ignore_content(self.path.name) or {}
            )  # type: ignore[var-annotated]
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
            "created": "firstCreated",
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
            "supportedModules": "supportedModules",
            "disable_monthly": "disableMonthly",
            "content_commit_hash": "contentCommitHash",
            "default_data_source_id": "defaultDataSource",
            "source": "source",
            "managed": "managed",
            "internal": "internal",
            "coupling_overrides": "coupling_overrides",
            "derived_source": "derived_source",
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


class DerivedPackParser:
    """A lightweight parser representing a derived (managed) pack.

    Derived packs are virtual constructs generated by the SDK for split-pack
    candidates.  They do not correspond to a physical directory on disk — they
    inherit most properties from the original ``PackParser`` and override only
    the fields that distinguish them (``object_id``, ``managed``, ``source``,
    ``is_derived``, ``derived_from``).

    The ``content_type`` is set to ``ContentType.PACK`` so the graph builder
    treats it like a regular pack node.
    """

    content_type = ContentType.PACK

    def __init__(
        self,
        original_parser: PackParser,
        derived_id: str,
    ) -> None:
        self._original = original_parser
        self._derived_id = derived_id

        # Copy essential attributes from the original parser
        self.path = original_parser.path
        self.name = f"{original_parser.name} {DERIVED_PACK_SUFFIX}"
        self.display_name = self.name
        self.description = original_parser.description
        self.support = original_parser.support
        self.created = original_parser.created
        self.updated = original_parser.updated
        self.legacy = original_parser.legacy
        self.email = original_parser.email
        self.eulaLink = original_parser.eulaLink
        self.author_image = original_parser.author_image
        self.price = original_parser.price
        self.hidden = original_parser.hidden
        self.server_min_version = original_parser.server_min_version
        self.current_version = original_parser.current_version
        self.version_info = original_parser.version_info
        self.commit = original_parser.commit
        self.downloads = original_parser.downloads
        self.tags = original_parser.tags
        self.default_data_source_id = original_parser.default_data_source_id
        self.keywords = original_parser.keywords
        self.search_rank = original_parser.search_rank
        self.videos = original_parser.videos
        self.excluded_dependencies = original_parser.excluded_dependencies
        self.modules = original_parser.modules
        self.integrations = original_parser.integrations
        self.premium = original_parser.premium
        self.vendor_id = original_parser.vendor_id
        self.partner_id = original_parser.partner_id
        self.partner_name = original_parser.partner_name
        self.preview_only = original_parser.preview_only
        self.disable_monthly = original_parser.disable_monthly
        self.content_commit_hash = original_parser.content_commit_hash
        self.hybrid = original_parser.hybrid
        self.pack_metadata_dict = original_parser.pack_metadata_dict.copy()
        self.supportedModules = original_parser.supportedModules
        self.coupling_overrides = original_parser.coupling_overrides

        # Override fields for derived identity
        self.managed = True
        # Derived packs are published under a feature name, not under the
        # originating pack's name: the Managed Content bucket lays out as
        # <bucket>/<bucket_path>/<source>/<pack_id>/. The link back to the
        # originating pack is preserved via derived_from below.
        self.source = resolve_derived_pack_source(
            getattr(original_parser, "derived_source", None)
        )
        self.internal = original_parser.internal
        self.is_derived = True
        self.derived_from = original_parser.object_id

        # Derived packs share content items with the original but have
        # their own relationships (the second IN_PACK edges).
        self.content_items = PackContentItems()
        self.relationships = Relationships()
        self.structure_errors: List[StructureError] = []
        self.ignored_errors_dict: dict = {}
        self.contributors: List[str] = (
            original_parser.contributors
            if hasattr(original_parser, "contributors")
            else []
        )
        self.latest_rn_version = original_parser.latest_rn_version
        self.deprecated = original_parser.deprecated
        self.private_pack_path = original_parser.private_pack_path

        # Inherit the original pack's relationships, except its pack-level
        # DEPENDS_ON edges. A derived pack ships to the Managed Content bucket
        # as a self-contained unit, so it declares no pack-level dependencies.
        # Inheriting them verbatim would also be wrong on its own terms: those
        # entries carry the *original* pack's object_id as their source, so the
        # graph would re-create the original's dependencies a second time
        # (build_depends_on_relationships_query MERGEs them, but
        # remove_existing_depends_on_relationships only clears edges with
        # from_metadata = false, so metadata edges are never recalculated).
        self.relationships.update(
            Relationships(
                {
                    relationship_type: entries
                    for relationship_type, entries in original_parser.relationships.items()
                    if relationship_type != RelationshipType.DEPENDS_ON
                }
            )
        )

    @property
    def object_id(self) -> Optional[str]:
        return self._derived_id

    @property
    def node_id(self) -> str:
        return self._derived_id

    @property
    def marketplaces(self) -> List:
        return self._original.marketplaces

    @property
    def url(self) -> str:
        return self._original.url

    @property
    def certification(self) -> str:
        return self._original.certification

    @property
    def author(self) -> str:
        return self._original.author

    @property
    def categories(self) -> list:
        return self._original.categories

    @property
    def use_cases(self) -> list:
        return self._original.use_cases

    @cached_property
    def field_mapping(self) -> dict:
        mapping = self._original.field_mapping.copy()
        return mapping
