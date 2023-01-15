import logging

from demisto_sdk.commands.common.constants import MarketplaceVersions

logger = logging.getLogger("demisto-sdk")


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

        replacement_configuration = {
            MarketplaceVersions.MarketplaceV2: "_x2",
        }

        suffix = replacement_configuration.get(marketplace)
        if suffix:
            suffix_len = len(suffix)
            data_keys = list(data.keys())
            for current_key in data_keys:
                if current_key.casefold().endswith(suffix):
                    current_key_no_suffix = current_key[:-suffix_len]
                    logger.debug(
                        f"Replacing {current_key_no_suffix} value from {data[current_key_no_suffix]} to {data[current_key]}."
                    )
                    data[current_key_no_suffix] = data[current_key]
                    data.pop(current_key, None)

                elif isinstance(data[current_key], dict):
                    data[current_key] = MarketplaceSuffixPreparer.prepare(
                        data[current_key], marketplace
                    )
                elif isinstance(data[current_key], list):
                    updated_list = []
                    for current_item in data[current_key]:
                        if isinstance(current_item, dict):
                            current_item = MarketplaceSuffixPreparer.prepare(
                                current_item, marketplace
                            )
                        updated_list.append(current_item)

        return data
