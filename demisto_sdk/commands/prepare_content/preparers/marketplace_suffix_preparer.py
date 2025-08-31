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

        def fix_recursively(datum: Any, parent_key: str = None) -> Any:
            if isinstance(datum, list):
                return [fix_recursively(item, parent_key) for item in datum]

            elif isinstance(datum, dict):
                for key in tuple(datum.keys()):
                    value = datum[key]
                    if isinstance(value, (list, dict)):
                        fix_recursively(value, key if parent_key is None else parent_key)
                    if SEPARATOR not in key:
                        continue
                    for suffix in suffixes:
                        suffix_len = len(suffix)
                        if isinstance(key, str) and key.casefold().endswith(suffix):
                            clean_key = key[:-suffix_len]
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
                        # Only preserve colon-containing keys if we are under 'keyTypeMap'
                        if parent_key == 'keyTypeMap':
                            pass  # Do nothing, preserve keys like 'Policy: EUC' or 'string:string' under keyTypeMap
                        else:
                            logger.debug(
                                f"Field {key} does not end with any relevant suffix, deleting"
                            )
                            datum.pop(key, None)
                return datum

        if not isinstance(result := fix_recursively(data), dict):  # to calm mypy
            raise ValueError(
                f"unexpected result type {type(result)}, expected dictionary"
            )
        return result
