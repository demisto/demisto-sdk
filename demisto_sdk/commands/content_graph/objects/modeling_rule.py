from typing import Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_x2 import ContentItemX2
from demisto_sdk.commands.unify.rule_unifier import RuleUnifier


class ModelingRule(ContentItemX2, content_type=ContentType.MODELING_RULE):  # type: ignore[call-arg]

    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

    def prepare_for_upload(self, marketplace: MarketplaceVersions = MarketplaceVersions.MarketplaceV2, **kwargs) -> dict:
        data = super().prepare_for_upload(marketplace)
        data = RuleUnifier.unify(self.path, data, marketplace)
        return data
