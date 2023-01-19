import logging
from typing import Dict

from demisto_sdk.commands.common.constants import MarketplaceVersions

logger = logging.getLogger("demisto-sdk")

MARKETPLACE_TO_SUFFIX: Dict[MarketplaceVersions, str] = {
    MarketplaceVersions.MarketplaceV2: "_x2",
}


class MarketplaceSuffixPreparer:
    @staticmethod
    def prepare(
        data: dict,
        marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    ) -> dict:
        """
        Iterate over all of the given content item fields and if there is a field with an alternative name,
        then use that value as the value of the original field (the corresponding one without the suffix).
        Args:
            data: content item data
            marketplace: Marketplace. Used to determine the specific suffix

        Returns: A (possibliy) modified content item data

        """
        if not (suffix := MARKETPLACE_TO_SUFFIX.get(marketplace)):
            return data
        suffix_len = len(suffix)

        def fix_recursively(datum: dict) -> dict:
            # performs the actual fix, without accessing the MARKETPLACE_TO_SUFFIX dictionary.
            for key in tuple(
                datum.keys()
            ):  # deliberately not iterating over .items(), as the dict changes during iteration
                value = datum[key]

                if key.casefold().endswith(suffix):
                    clean_key = key[:-suffix_len]  # without suffix
                    logger.debug(
                        f"Replacing {clean_key}={datum[clean_key]} to {value}."
                    )
                    datum[clean_key] = value
                    datum.pop(key, None)

                elif isinstance(value, dict):
                    datum[key] = fix_recursively(value)

                elif isinstance(value, list):
                    datum[key] = [fix_recursively(list_item) for list_item in value]

            return datum

        return fix_recursively(data)
