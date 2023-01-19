import logging
from typing import Dict, Union

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

        def fix_recursively(datum: Union[dict, str, list]) -> Union[dict, str, list]:
            if isinstance(datum, str):
                return datum

            elif isinstance(datum, list):
                return [fix_recursively(item) for item in datum]

            elif isinstance(datum, dict):
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

            return datum

        if not isinstance(result := fix_recursively(data), dict):  # to calm mypy
            raise ValueError(
                f"unexpected result type {type(result)}, expected dictionary"
            )
        return result
