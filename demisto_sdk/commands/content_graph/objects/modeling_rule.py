from typing import Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)
from demisto_sdk.commands.prepare_content.rule_unifier import RuleUnifier


class ModelingRule(ContentItemXSIAM, content_type=ContentType.MODELING_RULE):  # type: ignore[call-arg]
    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

    def prepare_for_upload(
        self,
        marketplace: MarketplaceVersions = MarketplaceVersions.MarketplaceV2,
        **kwargs
    ) -> dict:
        if not kwargs.get("unify_only"):
            data = super().prepare_for_upload(marketplace)
        else:
            data = self.data
        data = RuleUnifier.unify(self.path, data, marketplace)
        return data
