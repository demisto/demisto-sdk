from demisto_sdk.commands.common.constants import MarketplaceVersions

MARKETPLACES_SUPPORTING_FETCH_EVENTS = [
    MarketplaceVersions.MarketplaceV2,
    MarketplaceVersions.PLATFORM,
]

MARKETPLACES_SUPPORTING_FETCH_ASSETS = [
    MarketplaceVersions.MarketplaceV2,
    MarketplaceVersions.XPANSE,
    MarketplaceVersions.PLATFORM,
]

MARKETPLACES_SUPPORTING_QUICK_ACTIONS = [
    MarketplaceVersions.PLATFORM,
]


class MarketplaceCommandsAvailabilityPreparer:
    @staticmethod
    def prepare(
        data: dict,
        current_marketplace: MarketplaceVersions,
    ) -> dict:
        """
        Ensures all integration commands are available only in the correct marketplaces.
        Returns: A (possibliy) modified integration data

        """
        MarketplaceCommandsAvailabilityPreparer.prepare_fetch_events(
            data, current_marketplace
        )
        MarketplaceCommandsAvailabilityPreparer.prepare_fetch_assets(
            data, current_marketplace
        )
        MarketplaceCommandsAvailabilityPreparer.prepare_quick_actions(
            data, current_marketplace
        )
        return data

    @staticmethod
    def prepare_fetch_events(
        data: dict,
        current_marketplace: MarketplaceVersions,
    ) -> None:
        if current_marketplace not in MARKETPLACES_SUPPORTING_FETCH_EVENTS and data[
            "script"
        ].get("isfetchevents"):
            data["script"]["isfetchevents"] = False

    @staticmethod
    def prepare_fetch_assets(
        data: dict,
        current_marketplace: MarketplaceVersions,
    ) -> None:
        if current_marketplace not in MARKETPLACES_SUPPORTING_FETCH_ASSETS and data[
            "script"
        ].get("isfetchassets"):
            data["script"]["isfetchassets"] = False

    @staticmethod
    def prepare_quick_actions(
        data: dict,
        current_marketplace: MarketplaceVersions,
    ) -> None:
        if (
            current_marketplace not in MARKETPLACES_SUPPORTING_QUICK_ACTIONS
            and isinstance(data.get("script", {}).get("commands"), list)
        ):
            data["script"]["commands"] = [
                cmd for cmd in data["script"]["commands"] if not cmd.get("quickaction")
            ]
