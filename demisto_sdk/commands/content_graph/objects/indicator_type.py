from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, List, Optional, Set

import demisto_client
from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

json = JSON_Handler()


class IndicatorType(ContentItem, content_type=ContentType.INDICATOR_TYPE):  # type: ignore[call-arg]
    description: str = Field(alias="details")
    regex: Optional[str]
    reputation_script_name: Optional[str] = Field("", alias="reputationScriptName")
    expiration: Any
    enhancement_script_names: Optional[List[str]] = Field(
        alias="enhancementScriptNames"
    )
    version: Optional[int] = 0

    def metadata_fields(self) -> Set[str]:
        return (
            super()
            .metadata_fields()
            .union(
                {
                    "details",
                    "reputation_script_name",
                    "enhancement_script_names",
                }
            )
        )

    def _upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
    ) -> None:
        with TemporaryDirectory() as dir:
            file_path = Path(dir, self.normalize_name)
            with open(file_path, "w") as f:
                # Wrapping the dictionary with a list, as that's what the server expects
                json.dump([self.prepare_for_upload(marketplace=marketplace)], f)
            client.import_reputation_handler(str(file_path))

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "regex" in _dict or "reputations" in _dict and path.suffix == ".json":
            return True
        return False
