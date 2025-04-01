from abc import abstractmethod
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Set, Union

import demisto_client
from packaging.version import Version

from demisto_sdk.commands.common.handlers import (
    JSON_Handler,
    XSOAR_Handler,
    YAML_Handler,
)
from demisto_sdk.commands.upload.exceptions import IncompatibleUploadVersionException
from demisto_sdk.commands.upload.tools import parse_upload_response

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.pack import Pack
    from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData
    from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook

from pydantic import DirectoryPath, Field, fields, validator

from demisto_sdk.commands.common.constants import PACKS_FOLDER, MarketplaceVersions
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_file,
    get_pack_name,
    get_relative_path,
    replace_incident_to_alert,
    write_dict,
)
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    RelationshipType,
    append_supported_modules,
    replace_marketplace_references,
)
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent,
)
from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import (
    MarketplaceSuffixPreparer,
)

CONTENT_ITEMS_TO_SKIP_ID_MODIFICATION = [ContentType.PLAYBOOK]


class ContentItem(BaseContent):
    path: Path
    marketplaces: List[MarketplaceVersions]
    name: str
    fromversion: str
    toversion: str
    display_name: str
    deprecated: bool
    description: Optional[str] = ""
    is_test: bool = False
    pack: Any = Field(None, exclude=True, repr=False)
    support: str = ""
    is_silent: bool = False

    @validator("path", always=True)
    def validate_path(cls, v: Path, values) -> Path:
        if v.is_absolute():
            return v
        if not CONTENT_PATH.name:
            return CONTENT_PATH / v
        return CONTENT_PATH.with_name(values.get("source_repo", "content")) / v

    @staticmethod
    @abstractmethod
    def match(_dict: dict, path: Path) -> bool:
        """
        This function checks whether the file in the given path is of the content item type.
        """
        pass

    @property
    def pack_id(self) -> str:
        return self.in_pack.pack_id if self.in_pack else ""

    @validator("pack", always=True)
    def validate_pack(cls, v: Any, values) -> Optional["Pack"]:
        # Validate that we have the pack containing the content item.
        # The pack is either provided directly or needs to be located.

        if v and not isinstance(v, fields.FieldInfo):
            return v
        return cls.get_pack(values.get("relationships_data"), values.get("path"))

    @validator("support", always=True)
    def validate_support(cls, v: str, values) -> str:
        # Ensure the 'support' field is present.
        # If not directly provided, the support level from the associated pack will be used.
        if v:
            return v
        pack = values.get("pack")
        if pack and pack.support:
            return pack.support

        return ""

    @property
    def in_pack(self) -> Optional["Pack"]:
        """
        This returns the Pack which the content item is in.

        Returns:
            Pack: Pack model.
        """
        if not self.pack:
            self.pack = ContentItem.get_pack(self.relationships_data, self.path)
        return self.pack  # type: ignore[return-value]

    @staticmethod
    def get_pack(
        relationships_data: dict,
        path: Path,
    ) -> Optional["Pack"]:
        """
        Returns the Pack which the content item is in.

        Returns:
            Pack: Pack model.
        """
        pack = None
        if in_pack := relationships_data[RelationshipType.IN_PACK]:
            pack = next(iter(in_pack)).content_item_to  # type: ignore[return-value]
        if not pack:
            if pack_name := get_pack_name(path):
                pack = BaseContent.from_path(
                    CONTENT_PATH / PACKS_FOLDER / pack_name, metadata_only=True
                )  # type: ignore[assignment]
        return pack  # type: ignore[return-value]

    @property
    def ignored_errors(self) -> List[str]:
        if ignored_errors := self.get_ignored_errors(self.path.name):
            return ignored_errors
        file_path = get_relative_path(self.path, CONTENT_PATH)
        return self.get_ignored_errors(file_path)

    def ignored_errors_related_files(self, file_path: Path) -> List[str]:
        if ignored_errors := self.get_ignored_errors((Path(file_path)).name):
            return ignored_errors
        file_path = get_relative_path(file_path, CONTENT_PATH)
        return self.get_ignored_errors(file_path)

    def get_ignored_errors(self, path: Union[str, Path]) -> List[str]:
        try:
            return (
                list(
                    self.in_pack.ignored_errors_dict.get(  # type: ignore
                        f"file:{path}", []
                    ).items()
                )[0][1].split(",")
                or []
            )
        except:  # noqa: E722
            logger.debug(
                f"Failed to extract ignored errors list from {path} for {self.object_id}"
            )
            return []

    @property
    def pack_name(self) -> str:
        return self.in_pack.name if self.in_pack else ""

    @property
    def pack_version(self) -> Optional[Version]:
        return self.in_pack.pack_version if self.in_pack else None

    @property
    def uses(self) -> List["RelationshipData"]:
        """
        This returns the content items which this content item uses.
        In addition, we can tell if it's a mandatorily use or not.

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
            for r in self.relationships_data[RelationshipType.USES]
            if r.content_item_to.database_id == r.target_id
        ]

    @property
    def tested_by(self) -> List["TestPlaybook"]:
        """
        This returns the test playbooks which the content item is tested by.

        Returns:
            List[TestPlaybook]: List of TestPlaybook models.
        """
        return [
            r.content_item_to  # type: ignore[misc]
            for r in self.relationships_data[RelationshipType.TESTED_BY]
            if r.content_item_to.database_id == r.target_id
        ]

    @property
    def used_by(self) -> List["RelationshipData"]:
        """
        This returns the content items which this content item used by.
        In addition, we can tell if it's a mandatorily use or not.

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
            for r in self.relationships_data[RelationshipType.USES]
            if r.content_item_to.database_id == r.source_id
        ]

    @property
    def handler(self) -> XSOAR_Handler:
        # we use a high value so the code lines will not break
        return (
            JSON_Handler()
            if self.path.suffix.lower() == ".json"
            else YAML_Handler(width=50_000)
        )

    @property
    def data(self) -> dict:
        return get_file(self.path, keep_order=False)

    @property
    def text(self) -> str:
        return get_file(self.path, return_content=True)

    @property
    def ordered_data(self) -> dict:
        return get_file(self.path, keep_order=True)

    def save(self, fields_to_exclude: List[str] = []):
        super()._save(self.path, self.ordered_data, fields_to_exclude=fields_to_exclude)

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs,
    ) -> dict:
        if not self.path.exists():
            raise FileNotFoundError(f"Could not find file {self.path}")
        data = self.data
        # Replace incorrect marketplace references
        data = replace_marketplace_references(data, current_marketplace, str(self.path))
        if current_marketplace == MarketplaceVersions.PLATFORM:
            data = append_supported_modules(data, self.supportedModules)
        else:
            if "supportedModules" in data:
                del data["supportedModules"]
        return MarketplaceSuffixPreparer.prepare(data, current_marketplace)

    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        """Summary of a content item (the most important metadata fields)

        Args:
            marketplace: The marketplace to get the summary for.
        Returns:
            dict: Dictionary representation of the summary content item.
        """
        summary_res = self.dict(include=self.metadata_fields(), by_alias=True)
        if marketplace and marketplace != MarketplaceVersions.XSOAR:
            data = self.data
            if "id" in summary_res:
                summary_res["id"] = (
                    data.get("commonfields", {}).get("id") or self.object_id
                )
            if "name" in summary_res:
                summary_res["name"] = data.get("name") or self.name

            if incident_to_alert:
                summary_res.update(
                    {
                        "id": replace_incident_to_alert(summary_res["id"])
                        if self.content_type
                        not in CONTENT_ITEMS_TO_SKIP_ID_MODIFICATION
                        else summary_res["id"],
                        "name": replace_incident_to_alert(summary_res["name"]),
                        "description": replace_incident_to_alert(
                            summary_res["description"]
                        ),
                    }
                )

        return summary_res

    def metadata_fields(self) -> Set[str]:
        return {
            "object_id",
            "name",
            "description",
            "fromversion",
            "toversion",
            "deprecated",
            "supportedModules",
        }

    @property
    def normalize_name(self) -> str:
        """
        This will add the server prefix of the content item to its name
        In addition it will remove the existing server_names of the name.

        Args:
            name (str): content item name.
        Returns:
            str: The normalized name.
        """
        name = self.path.name
        server_names = ContentType.server_names()
        for _ in range(2):
            # we iterate twice to handle cases of doubled prefixes like `classifier-mapper-`
            for prefix in server_names:
                name = name.removeprefix(f"{prefix}-")
        normalized = f"{self.content_type.server_name}-{name}"
        logger.debug(f"Normalized file name from {name} to {normalized}")
        return normalized

    def dump(
        self,
        dir: DirectoryPath,
        marketplace: MarketplaceVersions,
    ) -> None:
        if not self.path.exists():
            logger.warning(f"Could not find file {self.path}, skipping dump")
            return
        dir.mkdir(exist_ok=True, parents=True)
        try:
            write_dict(
                dir / self.normalize_name,
                data=self.prepare_for_upload(current_marketplace=marketplace),
                handler=self.handler,
            )
            logger.debug(f"path to dumped file: {str(dir / self.normalize_name)}")
        except FileNotFoundError as e:
            logger.warning(f"Failed to dump {self.path} to {dir}: {e}")

    def to_id_set_entity(self) -> dict:
        """
        Transform the model to content item id_set.
        This is temporarily until the content graph is fully merged.

        Returns:
            dict: id_set entiity
        """
        id_set_entity = self.dict()
        id_set_entity["file_path"] = str(self.path)
        id_set_entity["pack"] = self.in_pack.object_id  # type: ignore[union-attr]
        return id_set_entity

    def is_incident_to_alert(self, marketplace: MarketplaceVersions) -> bool:
        """
        As long as the content item does not have an implementation of the `is_incident_to_alert` function,
        the return value will always be false,
        When there is, please override this method in the inheriting class and return `True`.
        Namely, there is no need for special preparation of an incident to alert for the content item.

        Args:
            marketplace (MarketplaceVersions): the destination marketplace.

        Returns:
            bool: False
        """
        return False

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        """
        This attribute sets the method when the upload flow is only of the following form
            >   with TemporaryDirectory("w") as f:
            >       dir_path = Path(f)
            >       self.dump(dir_path, marketplace=marketplace)
            >       client.<<SOME_METHOD>>(file=dir_path / self.normalize_name)

        When the flow is different, return None (default).
        """
        raise NotImplementedError

    def _upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
    ) -> None:
        """
        Called once the version is validated.
        Implementation may differ between content items.
        Most items use _client_upload_method, refer to its docstrings.
        """
        try:
            upload_method = self._client_upload_method(client=client)
        except NotImplementedError as e:
            raise NotImplementedError(
                f"missing overriding upload method for {self.content_type}"
            ) from e

        with TemporaryDirectory() as f:
            dir_path = Path(f)
            self.dump(
                dir_path,
                marketplace=marketplace,
            )
            response = upload_method(dir_path / self.normalize_name)
            parse_upload_response(
                response, path=self.path, content_type=self.content_type
            )  # raises on error

    def upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
        target_demisto_version: Version,
        **kwargs,
    ) -> None:
        """
        The only upload-related function to be used - the rest are abstract.
        This one checks for version compatibility and then calls _upload.
        """
        if not (
            Version(self.fromversion)
            <= target_demisto_version
            <= Version(self.toversion)
        ):
            raise IncompatibleUploadVersionException(self, target_demisto_version)
        self._upload(client, marketplace)
