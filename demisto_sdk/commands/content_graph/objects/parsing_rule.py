from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import MarketplaceVersions
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
    def match(_dict: dict, path: Path) -> bool:
        if "rules" in _dict:
            if "samples" in _dict and path.suffix == ".yml":
                return True
        return False

    def get_related_content(self) -> List[Path]:
        related_content_ls = super().get_related_content()
        related_content_ls.extend(
            [
                Path((str(self.path).replace(".yml", ".xif"))),
                Path((str(self.path).replace(".yml", "_Schema.json"))),
            ]
        )
        return related_content_ls
