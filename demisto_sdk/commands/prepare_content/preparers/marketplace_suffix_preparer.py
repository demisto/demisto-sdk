from typing import Any

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger

SEPARATOR = ":"


class MarketplaceSuffixPreparer:
    @staticmethod
    def prepare(
        data: dict,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    ) -> dict:
        """
        Iterate over all of the given content item fields and if there is a field with an alternative name,
        then use that value as the value of the original field (the corresponding one without the suffix).
        Args:
            data: content item data
            supported_marketplaces: list of the marketplaces this content item supports.
            current_marketplace: Marketplace. Used to determine the specific suffix

        Returns: A (possibliy) modified content item data

        """
        suffix = f"{SEPARATOR}{current_marketplace.value}"
        suffixes = [suffix]
        if current_marketplace == MarketplaceVersions.XSOAR_ON_PREM:
            suffixes.append(f"{SEPARATOR}{MarketplaceVersions.XSOAR.value}")
        if current_marketplace == MarketplaceVersions.XSOAR_SAAS:
            suffixes.append(f"{SEPARATOR}{MarketplaceVersions.XSOAR.value}")

        def fix_recursively(datum: Any) -> Any:
            if isinstance(datum, list):
                return [fix_recursively(item) for item in datum]

            elif isinstance(datum, dict):
                for key in tuple(
                    datum.keys()
                ):  # deliberately not iterating over .items(), as the dict changes during iteration
                    value = datum[key]
                    if isinstance(value, (list, dict)):
                        fix_recursively(value)
                    if SEPARATOR not in key:
                        continue
                    for suffix in suffixes:
                        # iterate each suffix to see if it's relevant for the key.
                        # the order of the suffixes matter, as XSOAR_SAAS and XSOAR_ON_PREM are more specific
                        suffix_len = len(suffix)
                        if isinstance(key, str) and key.casefold().endswith(suffix):
                            clean_key = key[:-suffix_len]  # without suffix
                            if clean_key not in datum:
                                logger.info(
                                    "Deleting field %s as it has no counterpart without suffix",
                                    key,
                                )
                                datum.pop(key, None)
                                continue
                            logger.debug(
                                f"Replacing {clean_key}={datum[clean_key]} to {value}."
                            )
                            datum[clean_key] = value
                            datum.pop(key, None)
                            break
                    else:
                        all_marketplace_suffixes = {f"{SEPARATOR}{mp.value}" for mp in MarketplaceVersions}
                        key_suffix = key[key.rfind(SEPARATOR):] if SEPARATOR in key else None
                        if key_suffix and key_suffix in all_marketplace_suffixes and key_suffix not in suffixes:
                            logger.debug(
                                f"Field {key} ends with a marketplace suffix ({key_suffix}) that is not the current marketplace, deleting"
                            )
                            datum.pop(key, None)
                        else:
                            logger.debug(
                                f"Field {key} does not end with any relevant suffix, keeping"
                            )
            return datum

        if not isinstance(result := fix_recursively(data), dict):  # to calm mypy
            raise ValueError(
                f"unexpected result type {type(result)}, expected dictionary"
            )
        return result
