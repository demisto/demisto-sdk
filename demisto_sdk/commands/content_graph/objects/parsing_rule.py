from pydantic import DirectoryPath
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.unify.rule_unifier import RuleUnifier


class ParsingRule(ContentItem):
    pass

    def summary(self):
        return self.dict(include=['name', 'description'])

    def dump(self, dir: DirectoryPath, marketplace: MarketplaceVersions) -> None:
        dir.mkdir(exist_ok=True, parents=True)
        RuleUnifier(input=self.path.parent, output=dir / super().normalize_file_name(self.path.name), marketplace=marketplace).unify()
