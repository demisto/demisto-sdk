from typing import Set

from pydantic.types import DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.unify.xdrc_template_unifier import XDRCTemplateUnifier


class XDRCTemplate(ContentItem, content_type=ContentType.XDRC_TEMPLATE):
    content_global_id: str
    os_type: str
    profile_type: str

    def metadata_fields(self) -> Set[str]:
        return {"name", "os_type", "profile_type"}

    def dump(self, dir: DirectoryPath, _: MarketplaceVersions) -> None:
        dir.mkdir(exist_ok=True, parents=True)
        XDRCTemplateUnifier(
            input=str(self.path.parent), output=dir
        ).unify()
