from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.constants import (
    MODELING_RULES_DIR,
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
    def match(_dict: dict, path: Path) -> Optional[ContentType]:
        if "rules" in _dict:
            if MODELING_RULES_DIR in Path(path).parts and Path(path).suffix == ".yml":
                return ContentType.MODELING_RULE
        return None
