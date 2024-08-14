from pathlib import Path
from typing import Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)
from demisto_sdk.commands.prepare_content.xdrc_template_unifier import (
    XDRCTemplateUnifier,
)


class XDRCTemplate(ContentItemXSIAM, content_type=ContentType.XDRC_TEMPLATE):
    content_global_id: str
    os_type: str
    profile_type: str

    def metadata_fields(self) -> Set[str]:
        return (
            super()
            .metadata_fields()
            .union(
                {
                    "content_global_id",
                    "os_type",
                    "profile_type",
                }
            )
        )

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.MarketplaceV2,
        **kwargs,
    ) -> dict:
        data = super().prepare_for_upload(current_marketplace)
        data = XDRCTemplateUnifier.unify(self.path, data, current_marketplace)
        return data

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            "profile_type" in _dict
            and "yaml_template" in _dict
            and path.suffix == ".json"
        ):
            return True
        return False
