from typing import Set

from pydantic import DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.unify.rule_unifier import RuleUnifier


class ModelingRule(ContentItem, content_type=ContentType.MODELING_RULE):  # type: ignore[call-arg]

    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

    def dump(self, dir: DirectoryPath, marketplace: MarketplaceVersions) -> None:
        dir.mkdir(exist_ok=True, parents=True)
        RuleUnifier(
            input=str(self.path.parent), output=str(dir), marketplace=marketplace
        ).unify()
