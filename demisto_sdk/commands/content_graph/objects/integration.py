from typing import TYPE_CHECKING, Callable, List, Optional

import demisto_client

from demisto_sdk.commands.content_graph.objects.base_content import BaseContent

if TYPE_CHECKING:
    # avoid circular imports
    from demisto_sdk.commands.content_graph.objects.script import Script

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)


class Command(BaseContent, content_type=ContentType.COMMAND):  # type: ignore[call-arg]
    name: str

    # From HAS_COMMAND relationship
    deprecated: bool = False
    description: Optional[str] = ""

    # missing attributes in DB
    node_id: str = ""
    object_id: str = Field("", alias="id")

    @property
    def integrations(self) -> List["Integration"]:
        return [
            r.content_item_to  # type: ignore[misc]
            for r in self.relationships_data[RelationshipType.HAS_COMMAND]
            if r.content_item_to.database_id == r.source_id
        ]

    def dump(self, *args) -> None:
        raise NotImplementedError()


class Integration(IntegrationScript, content_type=ContentType.INTEGRATION):  # type: ignore[call-arg]
    is_fetch: bool = False
    is_fetch_events: bool = False
    is_fetch_events_and_assets: bool = False
    is_feed: bool = False
    category: str
    commands: List[Command] = []

    @property
    def imports(self) -> List["Script"]:
        return [
            r.content_item_to  # type: ignore[misc]
            for r in self.relationships_data[RelationshipType.IMPORTS]
            if r.content_item_to.database_id == r.target_id
        ]

    def set_commands(self):
        commands = [
            Command(
                # the related to has to be a command
                name=r.content_item_to.name,  # type: ignore[union-attr,attr-defined]
                marketplaces=self.marketplaces,
                deprecated=r.deprecated,
                description=r.description,
            )
            for r in self.relationships_data[RelationshipType.HAS_COMMAND]
        ]
        self.commands = commands

    def metadata_fields(self):
        return {
            "name": True,
            "description": True,
            "category": True,
            "commands": {
                "__all__": {"name": True, "description": True}
            },  # for all commands, keep the name and description
        }

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs,
    ) -> dict:
        data = super().prepare_for_upload(current_marketplace, **kwargs)

        if supported_native_images := self.get_supported_native_images(
            marketplace=current_marketplace,
            ignore_native_image=kwargs.get("ignore_native_image") or False,
        ):
            logger.debug(
                f"Adding the following native images {supported_native_images} to integration {self.object_id}"
            )
            data["script"]["nativeimage"] = supported_native_images

        return data

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.integration_upload
