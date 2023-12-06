from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.constants import PARSING_RULES_DIR, MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)
from demisto_sdk.commands.prepare_content.rule_unifier import RuleUnifier


class ParsingRule(ContentItemXSIAM, content_type=ContentType.PARSING_RULE):  # type: ignore[call-arg]
    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.MarketplaceV2,
        **kwargs
    ) -> dict:
        if not kwargs.get("unify_only"):
            data = super().prepare_for_upload(current_marketplace)
        else:
            data = self.data
        data = RuleUnifier.unify(self.path, data, current_marketplace)
        return data

    @staticmethod
    def match(_dict: dict, path: Path) -> Optional[ContentType]:
        if "rules" in _dict:
            if (
                "samples" in _dict
                and PARSING_RULES_DIR in path.parts
                and path.suffix == ".yml"
            ):
                return ContentType.PARSING_RULE
        return None
