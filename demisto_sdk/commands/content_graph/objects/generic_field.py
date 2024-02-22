from pathlib import Path
from typing import Optional, Set

from pydantic import DirectoryPath, Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class GenericField(ContentItem, content_type=ContentType.GENERIC_FIELD):  # type: ignore[call-arg]
    definition_id: Optional[str] = Field(alias="definitionId")
    field_type: Optional[str] = Field(alias="type")
    version: Optional[int] = 0

    def metadata_fields(self) -> Set[str]:
        return super().metadata_fields().union({"field_type"})

    def dump(
        self,
        dir: DirectoryPath,
        marketplace: MarketplaceVersions,
    ) -> None:
        super().dump(
            dir=dir / self.path.parent.name,
            marketplace=marketplace,
        )

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "id" in _dict and isinstance(_dict["id"], str):
            if (
                "definitionId" in _dict
                and _dict["definitionId"]
                and _dict["definitionId"].lower() not in ["incident", "indicator"]
                and path.suffix == ".json"
            ):
                # we don't want to match the generic type
                if "color" not in _dict:
                    return True
        return False
