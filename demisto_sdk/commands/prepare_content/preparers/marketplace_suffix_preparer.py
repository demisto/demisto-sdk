from typing import Any

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger

SEPARATOR = ":"

MANAGED_KEY = "managed"
SOURCE_KEY = "source"

# Marketplaces that are always considered unmanaged. For these marketplaces the
# pack is forced to `managed: false` and the `source` field is removed, without
# any further suffix resolution.
ALWAYS_UNMANAGED_MARKETPLACES = {
    MarketplaceVersions.XSOAR,
    MarketplaceVersions.XSOAR_SAAS,
    MarketplaceVersions.XSOAR_ON_PREM,
    MarketplaceVersions.XPANSE,
}


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
                        all_marketplace_suffixes = {
                            f"{SEPARATOR}{mp.value}" for mp in MarketplaceVersions
                        }
                        key_suffix = (
                            key[key.rfind(SEPARATOR) :] if SEPARATOR in key else None
                        )
                        if (
                            key_suffix
                            and key_suffix in all_marketplace_suffixes
                            and key_suffix not in suffixes
                        ):
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

    @staticmethod
    def prepare_managed_and_source(
        data: dict,
        current_marketplace: MarketplaceVersions,
    ) -> dict:
        """
        Resolves the marketplace-suffixed ``managed`` and ``source`` fields of a
        pack metadata into their final, marketplace-specific values.

        The pack metadata may contain ``managed``/``source`` keys with an optional
        marketplace suffix (e.g. ``managed:platform``, ``source:platform``). This
        method collapses those into a single, plain ``managed`` (bool) and
        ``source`` (str) according to the current marketplace, following these rules:

        - If there is no ``managed`` key at all (neither plain nor suffixed), the
          data is returned unchanged (the pack is simply not managed).
        - A suffixed key (e.g. ``managed:platform``) overrides the plain key for
          that specific marketplace. The plain key is the default for every
          marketplace that has no specific suffix.
        - If any suffixed ``managed`` key exists, a plain ``managed`` key must also
          exist, otherwise a ``ValueError`` is raised.
        - Every suffix must be a valid ``MarketplaceVersions`` value, otherwise a
          ``ValueError`` is raised.
        - For marketplaces in ``ALWAYS_UNMANAGED_MARKETPLACES`` the pack is forced
          to ``managed: false`` and ``source`` is removed, without any resolution.
        - When the resolved ``managed`` is ``False``, the ``source`` field is
          removed entirely.
        - When the resolved ``managed`` is ``True``, the resolved ``source`` (the
          suffixed value if present, otherwise the plain value) is kept, if any.
        - All suffixed ``managed``/``source`` keys are removed from the output.

        Args:
            data: The pack metadata dictionary.
            current_marketplace: The marketplace the pack is being prepared for.

        Returns:
            The (possibly modified) pack metadata dictionary.
        """
        valid_suffixes = {f"{SEPARATOR}{mp.value}" for mp in MarketplaceVersions}

        def collect_keys(field: str) -> dict:
            """Maps each existing key of the given field to its key string.

            Returns a dict mapping the key suffix (e.g. ``:platform`` or ``""`` for
            the plain key) to the actual key in ``data``.
            """
            collected: dict = {}
            for key in data:
                if not isinstance(key, str):
                    continue
                # A None value means the field is not actually set (it only exists
                # because the model declares it). Treat it as absent.
                if data[key] is None:
                    continue
                if key == field:
                    collected[""] = key
                elif key.startswith(f"{field}{SEPARATOR}"):
                    suffix = key[len(field):]
                    if suffix not in valid_suffixes:
                        raise ValueError(
                            f"Invalid marketplace suffix in pack metadata field '{key}'. "
                            f"The suffix must be one of: "
                            f"{sorted(mp.value for mp in MarketplaceVersions)}."
                        )
                    collected[suffix] = key
            return collected

        def remove_suffixed_keys() -> None:
            """Removes every suffixed managed/source key from ``data``.

            This also drops keys whose value is None (e.g. model-declared suffix
            fields that were never set by the author).
            """
            for key in list(data.keys()):
                if not isinstance(key, str):
                    continue
                for field in (MANAGED_KEY, SOURCE_KEY):
                    if (
                        key.startswith(f"{field}{SEPARATOR}")
                        and key[len(field):] in valid_suffixes
                    ):
                        data.pop(key, None)
                        break

        managed_keys = collect_keys(MANAGED_KEY)
        source_keys = collect_keys(SOURCE_KEY)

        # No managed field at all - the pack is simply not managed. Clean up any
        # (None-valued) suffixed keys and leave the plain fields untouched.
        if not managed_keys:
            remove_suffixed_keys()
            return data

        # If any suffixed managed exists, a plain managed must also exist.
        has_suffixed_managed = any(suffix for suffix in managed_keys)
        if has_suffixed_managed and "" not in managed_keys:
            raise ValueError(
                "Pack metadata has a marketplace-suffixed 'managed' field but is "
                "missing a plain 'managed' field. A plain 'managed' value is "
                "required as the default for all other marketplaces."
            )

        current_suffix = f"{SEPARATOR}{current_marketplace.value}"

        # Resolve the values BEFORE mutating the dict: a marketplace-specific
        # value (if present) overrides the plain value.
        managed_resolved_key = managed_keys.get(current_suffix, managed_keys.get(""))
        resolved_managed = (
            data.get(managed_resolved_key, False) if managed_resolved_key else False
        )

        source_resolved_key = source_keys.get(current_suffix, source_keys.get(""))
        source_was_present = source_resolved_key is not None
        resolved_source = (
            data.get(source_resolved_key) if source_resolved_key else None
        )

        # Remove all suffixed managed/source keys from the output - only the
        # resolved plain values should remain.
        remove_suffixed_keys()

        # Marketplaces that are always unmanaged - force managed: false and drop source.
        if current_marketplace in ALWAYS_UNMANAGED_MARKETPLACES:
            data[MANAGED_KEY] = False
            data.pop(SOURCE_KEY, None)
            return data

        if not resolved_managed:
            data[MANAGED_KEY] = False
            data.pop(SOURCE_KEY, None)
            return data

        data[MANAGED_KEY] = True
        if source_was_present:
            data[SOURCE_KEY] = resolved_source

        return data
