from pathlib import Path
from typing import Dict

from demisto_sdk.commands.common.constants import MarketplaceVersions, RelatedFileType
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

    def get_related_content(self) -> Dict[RelatedFileType, Dict]:
        related_content_files = super().get_related_content()
        related_content_files.update(
            {
                RelatedFileType.SCHEMA: {
                    "path": [str(self.path).replace(".yml", "_Schema.json")],
                    "git_status": None,
                },
                RelatedFileType.XIF: {
                    "path": [str(self.path).replace(".yml", ".xif")],
                    "git_status": None,
                },
            }
        )
        return related_content_files
