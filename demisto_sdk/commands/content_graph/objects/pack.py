import shutil
from collections import defaultdict
from configparser import ConfigParser
from configparser import Error as ConfigParserError
from functools import cached_property
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, List, Optional, Union

import demisto_client
from demisto_client.demisto_api.rest import ApiException
from packaging.version import Version, parse
from pydantic import DirectoryPath, Field, validator

from demisto_sdk.commands.common.constants import (
    BASE_PACK,
    CONTRIBUTORS_README_TEMPLATE,
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    MANDATORY_PACK_METADATA_FIELDS,
    MARKETPLACE_MIN_VERSION,
    PACKS_PACK_IGNORE_FILE_NAME,
    ImagesFolderNames,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.git_util import (
    CommitOrBranchNotFoundError,
    GitFileNotFoundError,
    GitUtil,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    MarketplaceTagParser,
    get_file,
    get_relative_path,
    parse_ignore_list,
    write_dict,
)
from demisto_sdk.commands.content_graph.common import (
    PACK_METADATA_FILENAME,
    VERSION_CONFIG_FILENAME,
    ContentType,
    Nodes,
    Relationships,
    RelationshipType,
    replace_marketplace_references,
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
from demisto_sdk.commands.content_graph.parsers.related_files import (
    AuthorImageRelatedFile,
    PackIgnoreRelatedFile,
    ReadmeRelatedFile,
    RNRelatedFile,
    SecretsIgnoreRelatedFile,
    VersionConfigRelatedFile,
)
from demisto_sdk.commands.prepare_content.markdown_images_handler import (
    update_markdown_images_with_urls_and_rel_paths,
)
from demisto_sdk.commands.upload.constants import (
    CONTENT_TYPES_EXCLUDED_FROM_UPLOAD,
    CONTENT_TYPES_NOT_SUPPORTED_IN_UPLOAD,
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


class Pack(BaseContent, PackMetadata, content_type=ContentType.PACK):
    path: Path
    supportedModules: Optional[List[str]] = None
    contributors: Optional[List[str]] = None
    relationships: Relationships = Field(Relationships(), exclude=True)
    deprecated: bool = False
    ignored_errors_dict: dict = Field({}, exclude=True)
    pack_readme: str = Field("", exclude=True)
    latest_rn_version: str = Field("", exclude=True)
    content_items: PackContentItems = Field(
        PackContentItems(), alias="contentItems", exclude=True
    )
    pack_metadata_dict: Optional[dict] = Field({}, exclude=True)

    @classmethod
    def from_orm(cls, obj) -> "Pack":
        pack = super().from_orm(obj)
        for content_item in pack.content_items:
            content_item.pack = pack
        return pack

    @validator("path", always=True)
    def validate_path(cls, v: Path, values) -> Path:
        if v.is_absolute():
            return v
        if not CONTENT_PATH.name:
            return CONTENT_PATH / v
        return CONTENT_PATH.with_name(values.get("source_repo", "content")) / v

    @property
    def is_private(self) -> bool:
        return self.premium or False

    @property
    def pack_id(self) -> str:
        return self.object_id

    @property
    def ignored_errors(self) -> List[str]:
        if ignored_errors := self.get_ignored_errors(PACK_METADATA_FILENAME):
            return ignored_errors
        file_path = get_relative_path(self.path, CONTENT_PATH)
        return self.get_ignored_errors(file_path / PACK_METADATA_FILENAME)

    @cached_property
    def pack_level_ignored_errors(self) -> List[str]:
        """Error codes listed under the [pack] section of `.pack-ignore`.

        Codes returned here are ignored for the pack itself and for every
        content item belonging to it (including their related files).
        """
        section = self.ignored_errors_dict.get("pack")
        if section is None:
            return []
        for key, value in section.items():
            if key == "ignore":
                return parse_ignore_list(value)
        return []

    def old_pack_level_ignored_errors(self, prev_ver: Optional[str]) -> List[str]:
        """The [pack]-section error codes from `.pack-ignore` as of `prev_ver`.

        Reads the previous version straight from git (the parsed
        `pack_level_ignored_errors` only reflects the working tree, so it can't
        be used as the "before" side of a diff).

        Args:
            prev_ver: the git ref to read the old file from (branch,
                `remote/branch`, or sha). None means "no previous version".

        Returns:
            The old [pack] codes, or [] when `prev_ver` is None, the file did
            not exist at that ref, or it had no [pack] section.
        """
        if not prev_ver:
            return []
        git_util = GitUtil.from_content_path()
        pack_ignore_path = self.path / PACKS_PACK_IGNORE_FILE_NAME
        old_text = self._read_pack_ignore_at_ref(git_util, pack_ignore_path, prev_ver)
        if old_text is None:
            return []
        try:
            config = ConfigParser(allow_no_value=True)
            config.read_string(old_text)
        except ConfigParserError as e:
            # The old `.pack-ignore` at `prev_ver` is malformed INI. This is an
            # expected, data-driven failure (bad committed file), not a bug, so
            # we treat the old [pack] section as empty rather than crash.
            logger.debug(
                f"Malformed old .pack-ignore for {self.object_id} at {prev_ver}: {e}"
            )
            return []
        if config.has_section("pack"):
            for key in config["pack"]:
                if key == "ignore":
                    return parse_ignore_list(config["pack"][key])
        return []

    @staticmethod
    def _read_pack_ignore_at_ref(
        git_util: GitUtil, pack_ignore_path: Path, prev_ver: str
    ) -> Optional[str]:
        """Read `.pack-ignore` text at `prev_ver`, tolerating fork/offline setups.

        Resolves `prev_ver` via `handle_prev_ver`, then reads the remote ref
        first and falls back to the local ref, so the baseline is still found
        when the remote is behind (forks) or unreachable (offline).

        Args:
            git_util: the GitUtil used to resolve refs and read file content.
            pack_ignore_path: path to the pack's `.pack-ignore` file.
            prev_ver: the git ref to read from (branch, `remote/branch`, or sha).

        Returns:
            The file text, or None if it does not exist at that ref.
        """
        remote, branch = git_util.handle_prev_ver(prev_ver)
        ref = f"{remote}/{branch}" if remote else branch
        for candidate_ref, from_remote in ((ref, True), (branch, False)):
            try:
                if git_util.is_file_exist_in_commit_or_branch(
                    pack_ignore_path, candidate_ref, from_remote
                ):
                    return git_util.read_file_content(
                        pack_ignore_path, candidate_ref, from_remote
                    ).decode("utf-8")
            except (
                CommitOrBranchNotFoundError,
                GitFileNotFoundError,
                UnicodeDecodeError,
            ) as e:
                # Expected, data-driven reasons this candidate ref can't be read:
                # the ref/commit doesn't exist here (common on forks/offline for
                # the remote candidate), the file isn't present at that ref, or
                # its bytes aren't valid UTF-8. Any of these just means "try the
                # next candidate / no old file"; unexpected errors propagate.
                logger.debug(
                    f"Could not read {pack_ignore_path} at {candidate_ref} "
                    f"(from_remote={from_remote}): {e}"
                )
        return None

    def ignored_errors_related_files(self, file_path: Path) -> List[str]:
        if ignored_errors := self.get_ignored_errors((Path(file_path)).name):
            return ignored_errors
        file_path = get_relative_path(file_path, CONTENT_PATH)
        return self.get_ignored_errors(file_path)

    def get_ignored_errors(self, path: Union[str, Path]) -> List[str]:
        try:
            return (
                list(
                    self.ignored_errors_dict.get(  # type: ignore
                        f"file:{path}", []
                    ).items()
                )[0][1].split(",")
                or []
            )
        except:  # noqa: E722
            logger.debug(f"Failed to extract ignored errors list from path {path}")
            return []

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
                    source: BaseNode
                    target: BaseNode

                    # this is the attribute we're interested in when querying
                    content_item: BaseNode

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

    def _clean_empty_supportedModuels_from_commands(self, content_items: dict):
        if not content_items:
            return
        for integration in content_items.get("integration", []):
            if "commands" in integration:
                for command in integration["commands"]:
                    if (
                        "supportedModules" in command
                        and not command["supportedModules"]
                    ):
                        del command["supportedModules"]

    def _dump_pack_metadata(
        self, source: Path, destination: Path, strip_internal: bool = False
    ) -> None:
        """Copies the pack_metadata.json file to the destination.

        When ``strip_internal`` is true, the ``internal`` field is removed so
        the uploaded pack will be visible to the user. Otherwise the file is
        copied verbatim.

        Falls back to a plain copy if the source cannot be parsed as JSON,
        or if ``strip_internal`` is false.

        Args:
            source (Path): The path to the original pack_metadata.json.
            destination (Path): The path to write the (possibly modified)
                pack_metadata.json.
            strip_internal (bool): If true, remove the ``internal`` field from
                the destination file. Should only be set by the
                ``demisto-sdk upload`` flow.
        """
        if not strip_internal:
            shutil.copy(source, destination)
            return

        try:
            pack_metadata = get_file(source, raise_on_error=True)
        except Exception as e:
            logger.debug(
                f"Failed reading {source} as JSON ({e}); falling back to plain copy"
            )
            shutil.copy(source, destination)
            return

        if not isinstance(pack_metadata, dict):
            logger.debug(f"{source} is not a JSON object; falling back to plain copy")
            shutil.copy(source, destination)
            return

        if pack_metadata.pop("internal", None):
            logger.debug(f"Removed 'internal' field from {source} before upload")
        write_dict(destination, data=pack_metadata, indent=4)

    def dump_metadata(
        self,
        path: Path,
        marketplace: MarketplaceVersions,
        strip_internal: bool = False,
    ) -> None:
        """Dumps the pack metadata file.

        Args:
            path (Path): The path of the file to dump the metadata.
            marketplace (MarketplaceVersions): The marketplace to which the pack should belong to.
            strip_internal (bool): If true, the ``internal`` field is excluded
                from the dumped ``metadata.json`` so the uploaded pack is
                visible to users, and scripts marked with ``isInternal: true``
                are still listed in ``metadata.json``'s content items.
                Should only be set by the ``demisto-sdk upload`` flow.
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
        if strip_internal:
            # Strip `internal` so the uploaded pack will be visible to the user.
            excluded_fields_from_metadata.add("internal")
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
            self._format_metadata(
                marketplace,
                self.content_items,
                self.depends_on,
                strip_internal=strip_internal,
            )
        )
        self._clean_empty_supportedModuels_from_commands(
            metadata.get("contentItems", {})
        )
        # Replace incorrect marketplace references
        metadata = replace_marketplace_references(metadata, marketplace, str(self.path))
        if "supportedModules" in metadata and not metadata["supportedModules"]:
            del metadata["supportedModules"]
        write_dict(path, data=metadata, indent=4, sort_keys=True)

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
                # Replace incorrect marketplace references
                updated_text = replace_marketplace_references(
                    text, marketplace, str(self.path / "README.md")
                )

                if (
                    marketplace == MarketplaceVersions.XSOAR
                    and MarketplaceVersions.XSOAR_ON_PREM in self.marketplaces
                ):
                    marketplace = MarketplaceVersions.XSOAR_ON_PREM
                parsed_text = MarketplaceTagParser(marketplace).parse_text(updated_text)
                if len(text) != len(parsed_text):
                    f.seek(0)
                    f.write(parsed_text)
                    f.truncate()
            except Exception as e:
                logger.error(f"Failed dumping readme: {e}")

        update_markdown_images_with_urls_and_rel_paths(
            path, marketplace, self.object_id, file_type=ImagesFolderNames.README_IMAGES
        )

    def dump_release_notes(self, path: Path, marketplace: MarketplaceVersions) -> None:
        # TODO - Update this to dump the release notes for the platform marketplace
        # starting from platform supported version only.
        try:
            shutil.copytree(self.path / "ReleaseNotes", path)
        except FileNotFoundError:
            logger.debug(f'No such file {self.path / "ReleaseNotes"}')

    def dump(
        self,
        path: Path,
        marketplace: MarketplaceVersions,
        **kwargs,
    ):
        """Dumps the pack to ``path`` for upload/artifact creation.

        Args:
            path: Output directory.
            marketplace: Destination marketplace.
            **kwargs: Optional flags forwarded to the inner dump steps:
                - ``tpb`` (bool): When true, include test playbooks in the
                  dump.
                - ``strip_internal`` (bool): When true, the ``internal`` and
                  ``isInternal`` fields are removed from the dumped script
                  YAMLs (and ``internal`` from pack metadata files), and
                  scripts marked ``isInternal: true`` are still listed in
                  the pack ``metadata.json`` content items. Should only be
                  set by the ``demisto-sdk upload`` flow so that uploaded
                  content is visible to users; other flows (prepare-content,
                  artifact builds) keep the fields intact.
        """
        tpb: bool = kwargs.pop("tpb", False)
        strip_internal: bool = kwargs.get("strip_internal", False)

        if not self.path.exists():
            logger.warning(f"Pack {self.name} does not exist in {self.path}")
            return

        try:
            path.mkdir(exist_ok=True, parents=True)

            content_types_excluded_from_upload = (
                CONTENT_TYPES_EXCLUDED_FROM_UPLOAD.copy()
            )

            if tpb:
                content_types_excluded_from_upload.discard(ContentType.TEST_PLAYBOOK)

            for content_item in self.content_items:
                if content_item.content_type in content_types_excluded_from_upload:
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

                # The content structure is different from the server
                if folder == "CaseLayouts":
                    folder = "Layouts"
                dir = path / folder
                content_item.upload_path = dir / content_item.normalize_name
                content_item.dump(
                    dir=dir,
                    marketplace=marketplace,
                    **kwargs,
                )
            self.dump_metadata(
                path / "metadata.json", marketplace, strip_internal=strip_internal
            )
            self.dump_readme(path / "README.md", marketplace)
            self._dump_pack_metadata(
                self.path / PACK_METADATA_FILENAME,
                path / PACK_METADATA_FILENAME,
                strip_internal=strip_internal,
            )
            try:
                shutil.copy(
                    self.path / VERSION_CONFIG_FILENAME, path / VERSION_CONFIG_FILENAME
                )
            except FileNotFoundError:
                logger.debug(f"No such file {self.path / VERSION_CONFIG_FILENAME}")

            self.dump_release_notes(path / "ReleaseNotes", marketplace)

            try:
                shutil.copy(self.path / "Author_image.png", path / "Author_image.png")
            except FileNotFoundError:
                logger.debug(f'No such file {self.path / "Author_image.png"}')

            try:
                shutil.copytree(self.path / "doc_files", path / "doc_files")
            except FileNotFoundError:
                logger.debug(f'No such directory {self.path / "doc_files"}')

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
        zip: bool = True,
        tpb: bool = False,
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
                tpb=tpb,
            )
        else:
            self._upload_item_by_item(
                client=client,
                marketplace=marketplace,
                target_demisto_version=target_demisto_version,
                tpb=tpb,
            )

    def _zip_and_upload(
        self,
        client: demisto_client,
        target_demisto_version: Version,
        skip_validations: bool,
        marketplace: MarketplaceVersions,
        destination_dir: DirectoryPath,
        tpb: bool = False,
    ) -> bool:
        # this should only be called from Pack.upload
        logger.debug(f"Uploading zipped pack {self.object_id}")

        # 1) dump the pack into a temporary file
        with TemporaryDirectory() as temp_dump_dir:
            temp_dir_path = Path(temp_dump_dir)
            # strip_internal=True: this is an upload flow, so the `internal`
            # and `isInternal` fields should be removed from the dumped
            # script YAMLs and pack metadata so the uploaded content is
            # visible to users.
            self.dump(
                temp_dir_path,
                marketplace=marketplace,
                tpb=tpb,
                strip_internal=True,
            )

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
        tpb: bool = False,
    ) -> bool:
        # this should only be called from Pack.upload
        logger.debug(
            f"Uploading pack {self.object_id} element-by-element, as -z was not specified"
        )
        upload_failures: List[FailedUploadException] = []
        uploaded_successfully: List[ContentItem] = []
        incompatible_content_items = []

        content_types_excluded_from_upload = CONTENT_TYPES_EXCLUDED_FROM_UPLOAD.copy()
        if tpb:
            content_types_excluded_from_upload.discard(ContentType.TEST_PLAYBOOK)

        for item in self.content_items:
            if item.content_type in CONTENT_TYPES_NOT_SUPPORTED_IN_UPLOAD:
                upload_failures.append(
                    FailedUploadException(
                        item.path,
                        response_body={},
                        additional_info=(
                            f"{item.content_type} is not a content item and therefore cannot be uploaded as part of a pack"
                        ),
                    )
                )
                continue

            if item.content_type in content_types_excluded_from_upload:
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
                if marketplace in [
                    MarketplaceVersions.MarketplaceV2,
                    MarketplaceVersions.PLATFORM,
                ]:
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

    def save(self):
        file_path = self.path / PACK_METADATA_FILENAME
        data = get_file(file_path)
        # Never inject ``firstCreated`` if it was not already in the original
        # file.  The field_mapping maps ``created`` → ``firstCreated``, so
        # excluding ``created`` from _save() prevents the injection.
        fields_to_exclude = [] if "firstCreated" in data else ["created"]
        super()._save(
            file_path,
            data,
            predefined_keys_to_keep=MANDATORY_PACK_METADATA_FIELDS,
            fields_to_exclude=fields_to_exclude,
        )  # type: ignore

    @cached_property
    def readme(self) -> ReadmeRelatedFile:
        return ReadmeRelatedFile(self.path, is_pack_readme=True, git_sha=self.git_sha)

    @cached_property
    def author_image_file(self) -> AuthorImageRelatedFile:
        return AuthorImageRelatedFile(self.path, git_sha=self.git_sha)

    @cached_property
    def pack_ignore(self) -> PackIgnoreRelatedFile:
        return PackIgnoreRelatedFile(self.path, git_sha=self.git_sha)

    @cached_property
    def secrets_ignore(self) -> SecretsIgnoreRelatedFile:
        return SecretsIgnoreRelatedFile(self.path, git_sha=self.git_sha)

    @cached_property
    def version_config(self) -> VersionConfigRelatedFile:
        return VersionConfigRelatedFile(
            self.path,
            git_sha=self.git_sha,
            prev_ver=self.old_base_content_object.git_sha
            if self.old_base_content_object
            else None,
        )

    @cached_property
    def release_note(self) -> RNRelatedFile:
        return RNRelatedFile(
            self.path,
            git_sha=self.git_sha,
            prev_ver=self.old_base_content_object.git_sha
            if self.old_base_content_object
            else None,
            latest_rn=self.latest_rn_version,
        )
