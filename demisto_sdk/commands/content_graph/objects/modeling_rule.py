from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)
from demisto_sdk.commands.prepare_content.rule_unifier import RuleUnifier

json = JSON_Handler()


class ModelingRule(ContentItemXSIAM, content_type=ContentType.MODELING_RULE):  # type: ignore[call-arg]
    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        summary = super().summary(marketplace, incident_to_alert)
        summary["datasets"] = list(json.loads(self.data.get("schema") or "{}").keys())
        return summary

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
        if "rules" in _dict and Path(path).suffix == ".yml":
            # we don't want to match the correlation rule
            if (
                not (
                    "global_rule_id" in _dict
                    or (
                        isinstance(_dict, list)
                        and _dict
                        and "global_rule_id" in _dict[0]
                    )
                )
                and "samples" not in _dict
            ):
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
