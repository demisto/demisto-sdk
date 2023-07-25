from abc import abstractmethod
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Callable, List, Optional, Set

import demisto_client
from packaging.version import Version

from demisto_sdk.commands.common.handlers import (
    JSON_Handler,
    XSOAR_Handler,
    YAML_Handler,
)
from demisto_sdk.commands.content_graph.parsers.content_item import (
    InvalidContentItemException,
)
from demisto_sdk.commands.upload.exceptions import IncompatibleUploadVersionException
from demisto_sdk.commands.upload.tools import parse_upload_response

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.pack import Pack
    from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData
    from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook

from pydantic import DirectoryPath, validator

from demisto_sdk.commands.common.constants import PACKS_FOLDER, MarketplaceVersions
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_file,
    get_pack_name,
    replace_incident_to_alert,
)
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent,
)
from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import (
    MarketplaceSuffixPreparer,
)


class ContentItem(BaseContent):
    path: Path
    marketplaces: List[MarketplaceVersions]
    name: str
    fromversion: str
    toversion: str
    display_name: str
    deprecated: bool
    description: Optional[str]
    is_test: bool = False

    @validator("path", always=True)
    def validate_path(cls, v: Path) -> Path:
        if v.is_absolute():
            return v
        return CONTENT_PATH / v

    @property
    def pack_id(self) -> str:
        return self.in_pack.pack_id if self.in_pack else ""

    @property
    def pack_name(self) -> str:
        return self.in_pack.name if self.in_pack else ""

    @property
    def pack_version(self) -> Optional[Version]:
        return self.in_pack.pack_version if self.in_pack else None

    @property
    def in_pack(self) -> Optional["Pack"]:
        """
        This returns the Pack which the content item is in.

        Returns:
            Pack: Pack model.
        """
        if in_pack := self.relationships_data[RelationshipType.IN_PACK]:
            return next(iter(in_pack)).content_item_to  # type: ignore[return-value]
        if pack_name := get_pack_name(self.path):
            try:
                return BaseContent.from_path(
                    CONTENT_PATH / PACKS_FOLDER / pack_name
                )  # type: ignore[return-value]
            except InvalidContentItemException:
                logger.warning(
                    f"Could not parse pack {pack_name} for content item {self.path}"
                )
                return None
        logger.warning(f"Could not find pack for content item {self.path}")
        return None

    @property
    def uses(self) -> List["RelationshipData"]:
        """
        This returns the content items which this content item uses.
        In addition, we can tell if it's a mandatorily use or not.

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

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs,
    ) -> dict:
        if not self.path.exists():
            raise FileNotFoundError(f"Could not find file {self.path}")
        data = self.data
        logger.debug(f"preparing {self.path}")
        return MarketplaceSuffixPreparer.prepare(
            data, current_marketplace, self.marketplaces
        )

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
                    data.get("commonfields", {}).get("id_x2") or self.object_id
                )
            if "name" in summary_res:
                summary_res["name"] = data.get("name_x2") or self.name

            if incident_to_alert:
                if "name" in summary_res:
                    summary_res["name"] = replace_incident_to_alert(summary_res["name"])
                if "description" in summary_res:
                    summary_res["description"] = replace_incident_to_alert(
                        summary_res["description"]
                    )

        return summary_res

    @abstractmethod
    def metadata_fields(self) -> Set[str]:
        raise NotImplementedError("Should be implemented in subclasses")

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
                try:
                    name = name.removeprefix(f"{prefix}-")  # type: ignore[attr-defined]
                except AttributeError:
                    # not supported in python 3.8
                    name = (
                        name[len(prefix) + 1 :]
                        if name.startswith(f"{prefix}-")
                        else name
                    )
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
            with (dir / self.normalize_name).open("w") as f:
                self.handler.dump(
                    self.prepare_for_upload(current_marketplace=marketplace),
                    f,
                )
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
