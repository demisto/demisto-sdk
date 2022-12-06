from typing import Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_x2 import ContentItemX2
from demisto_sdk.commands.unify.xdrc_template_unifier import XDRCTemplateUnifier


class XDRCTemplate(ContentItemX2, content_type=ContentType.XDRC_TEMPLATE):
    content_global_id: str
    os_type: str
    profile_type: str

    def metadata_fields(self) -> Set[str]:
        return {"name", "os_type", "profile_type"}

    def prepare_for_upload(self, marketplace: MarketplaceVersions = MarketplaceVersions.MarketplaceV2, **kwargs) -> dict:
        data = super().prepare_for_upload(marketplace)
        data = XDRCTemplateUnifier.unify(self.path, data, marketplace)
        return data
