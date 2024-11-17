from functools import cached_property
from pathlib import Path

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType, replace_incorrect_marketplace
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)
from demisto_sdk.commands.content_graph.parsers.related_files import (
    SchemaRelatedFile,
    XifRelatedFile,
)
from demisto_sdk.commands.prepare_content.rule_unifier import RuleUnifier


class ParsingRule(ContentItemXSIAM, content_type=ContentType.PARSING_RULE):  # type: ignore[call-arg]
    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.MarketplaceV2,
        **kwargs,
    ) -> dict:
        if not kwargs.get("unify_only"):
            data = super().prepare_for_upload(current_marketplace)
        else:
            data = self.data
        # Replace incorrect marketplace references
        data = replace_incorrect_marketplace(data, current_marketplace, str(self.path))
        data = RuleUnifier.unify(self.path, data, current_marketplace)
        return data

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "rules" in _dict:
            if "samples" in _dict and path.suffix == ".yml":
                return True
        return False

    @cached_property
    def xif_file(self) -> XifRelatedFile:
        return XifRelatedFile(self.path, git_sha=self.git_sha)

    @cached_property
    def schema_file(self) -> SchemaRelatedFile:
        return SchemaRelatedFile(self.path, git_sha=self.git_sha)
