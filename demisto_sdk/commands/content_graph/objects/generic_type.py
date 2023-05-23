from typing import Optional, Set

from pydantic import DirectoryPath, Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class GenericType(ContentItem, content_type=ContentType.GENERIC_TYPE):  # type: ignore[call-arg]
    definition_id: Optional[str] = Field(alias="definitionId")

    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

    def dump(
        self,
        dir: DirectoryPath,
        marketplace: MarketplaceVersions,
    ) -> None:
        super().dump(
            dir=dir / self.path.parent.name,
            marketplace=marketplace,
        )
