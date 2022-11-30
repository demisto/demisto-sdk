from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.unify.yaml_unifier import YAMLUnifier


class WidgetUnifier(YAMLUnifier):
    
    def _prepare(self):
        super()._prepare()
        if self.marketplace == MarketplaceVersions.MarketplaceV2:
            self.data["name"].replace("Incidents", "Alerts")