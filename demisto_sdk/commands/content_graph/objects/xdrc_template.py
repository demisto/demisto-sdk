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
        return {"name", "os_type", "profile_type"}

    def prepare_for_upload(
        self,
        marketplace: MarketplaceVersions = MarketplaceVersions.MarketplaceV2,
        **kwargs
    ) -> dict:
        data = super().prepare_for_upload(marketplace)
        data = XDRCTemplateUnifier.unify(self.path, data, marketplace)
        return data
