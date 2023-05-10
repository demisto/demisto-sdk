from typing import List, Set

from demisto_sdk.commands.common.constants import SKIP_PREPARE_SCRIPT_NAME, MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_scripts_prepare import (
    MarketplaceIncidentToAlertScriptsPreparer
)
from pydantic import DirectoryPath


class Script(IntegrationScript, content_type=ContentType.SCRIPT):  # type: ignore[call-arg]
    tags: List[str]
    skip_prepare: List[str]

    def metadata_fields(self) -> Set[str]:
        return {"name", "description", "tags"}

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
                f"Adding the following native images {supported_native_images} to script {self.object_id}"
            )
            data["nativeimage"] = supported_native_images

        return data

    @property
    def imported_by(self) -> List[BaseContent]:
        return [
            r.content_item_to
            for r in self.relationships_data[RelationshipType.IMPORTS]
            if r.content_item_to.database_id == r.source_id
        ]

    def dump(self, dir: DirectoryPath, marketplace: MarketplaceVersions) -> None:
        dir.mkdir(exist_ok=True, parents=True)
        data = self.prepare_for_upload(current_marketplace=marketplace)

        # Keeps the original name of the script to redefine it at the end of the dump process
        original_path = self.path
        for data in MarketplaceIncidentToAlertScriptsPreparer.prepare(
                data, marketplace, self.is_incident_to_alert(marketplace)):

            # Sets the name of the script to the new name so that it will be normalized
            self.path = self.path.with_name(f"{data.get('name')}.yml")
            try:
                with (dir / self.normalize_name).open("w") as f:
                    self.handler.dump(data, f)
            except FileNotFoundError as e:
                logger.warning(f"Failed to dump {self.path} to {dir}: {e}")

        # Redefines the script name to the original name to continue the prepare process
        self.path = original_path

    def is_incident_to_alert(self, marketplace: MarketplaceVersions) -> bool:
        """
        Checks whether the script needs the preparation
        of an `incident to alert`,
        and this affects the `metadata.json` and the `dump` process of the script.

        Args:
            marketplace (MarketplaceVersions): the destination marketplace.

        Returns:
            bool: True if all conditions are true otherwise False
        """
        return all(
            (
                marketplace == MarketplaceVersions.MarketplaceV2,
                'incident' in self.name.lower(),
                SKIP_PREPARE_SCRIPT_NAME not in self.skip_prepare,
                not self.deprecated,
            )
        )
