from typing import Any

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger

SEPARATOR = ":"

MANAGED_KEY = "managed"
SOURCE_KEY = "source"

# Marketplaces designated as unmanaged. For these marketplaces,
# packs are forced to `managed: false` and the `source` field is removed, without
# any further suffix resolution.
ALWAYS_UNMANAGED_MARKETPLACES = {
    MarketplaceVersions.XSOAR,
    MarketplaceVersions.XSOAR_SAAS,
    MarketplaceVersions.XSOAR_ON_PREM,
    MarketplaceVersions.XPANSE,
    MarketplaceVersions.MarketplaceV2,
}


def _valid_suffixes() -> set:
    """Returns the marketplace suffixes allowed on `managed`/`source` keys.

    A suffix looks like `:platform`. Always-unmanaged marketplaces are excluded,
    as they never carry these fields. Computed on each call (reads the current
    `MarketplaceVersions`) so that dynamically registered marketplaces are honored.
    """
    return {
        f"{SEPARATOR}{mp.value}"
        for mp in MarketplaceVersions
        if mp not in ALWAYS_UNMANAGED_MARKETPLACES
    }


def _map_field_keys_by_suffix(data: dict, field: str) -> dict:
    """Finds all set keys for ``field`` and maps each marketplace suffix to its key.

    For example, ``managed`` and ``managed:platform`` become
    ``{"": "managed", ":platform": "managed:platform"}``. The empty-string key is
    the plain (default) value; a suffix like ``:platform`` is marketplace-specific.

    Keys whose value is ``None`` are skipped (they only exist because the model
    declares them). Returns the mapping so the caller can pick the right key per
    marketplace. Raises ``ValueError`` on an unknown suffix.
    """
    valid_suffixes = _valid_suffixes()
    collected: dict = {}
    for key in data:
        if data[key] is None:
            continue
        if key == field:
            collected[""] = key
        elif key.startswith(f"{field}{SEPARATOR}"):
            suffix = key[len(field) :]
            if suffix not in valid_suffixes:
                raise ValueError(
                    f"Invalid marketplace suffix in pack metadata field "
                    f"'{key}'. The suffix must be one of: "
                    f"{sorted(s.lstrip(SEPARATOR) for s in valid_suffixes)}."
                )
            collected[suffix] = key
    return collected


def _remove_managed_and_source_keys(data: dict) -> None:
    """Removes every ``managed``/``source`` key from ``data`` (plain and suffixed).

    Used to clear all variants before writing back the single resolved values,
    so the output has only a plain ``managed`` and ``source``.
    """
    for key in list(data.keys()):
        if (
            key in (MANAGED_KEY, SOURCE_KEY)
            or key.startswith(f"{MANAGED_KEY}{SEPARATOR}")
            or key.startswith(f"{SOURCE_KEY}{SEPARATOR}")
        ):
            data.pop(key, None)


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
        Sets the final ``managed`` and ``source`` values for the current marketplace.

        The pack metadata can hold ``managed``/``source`` keys with a marketplace
        suffix (e.g. ``managed:platform``, ``source:platform``). This method picks the
        right value for ``current_marketplace`` and leaves a single plain
        ``managed`` (bool) and ``source`` (str).

        How a value is picked:
        - A suffixed key wins for its own marketplace; the plain key is the default
          for every other marketplace.
        - Marketplaces in ``ALWAYS_UNMANAGED_MARKETPLACES`` are always forced to
          ``managed: false``.
        - ``source`` is kept only when the result is ``managed: true``; otherwise it
          is dropped.
        - All suffixed keys are removed at the end, leaving only the plain values.

        Raises ``ValueError`` when:
        - A suffix is not a valid marketplace.
        - A suffixed ``managed`` exists without a plain ``managed`` default.
        - A ``source`` exists without any ``managed``.
        - The result is ``managed: true`` but has no ``source``.
        - There is a ``source`` for this marketplace but the result is ``managed: false``.

        Args:
            data: The pack metadata dictionary.
            current_marketplace: The marketplace the pack is being prepared for.

        Returns:
            The same dictionary with ``managed``/``source`` resolved to plain
            values. Returned unchanged when neither field is present.
        """
        managed_keys = _map_field_keys_by_suffix(data, MANAGED_KEY)
        source_keys = _map_field_keys_by_suffix(data, SOURCE_KEY)

        if source_keys and not managed_keys:
            raise ValueError(
                "Pack metadata has a 'source' field but no 'managed' field. "
                "A 'source' is only valid for a managed pack (managed: true)."
            )

        if not managed_keys:
            return data

        # A suffixed managed requires a plain managed as the default for all
        # other marketplaces.
        if any(managed_keys) and "" not in managed_keys:
            suffixed_managed = next(
                (managed_keys[suffix] for suffix in managed_keys if suffix), None
            )
            raise ValueError(
                f"Pack metadata has a marketplace-suffixed 'managed' field "
                f"('{suffixed_managed}') but is missing a plain 'managed' field. "
                f"A plain 'managed' value is required as the default for all "
                f"other marketplaces."
            )

        current_suffix = f"{SEPARATOR}{current_marketplace.value}"

        # Resolve the values BEFORE mutating the dict: a marketplace-specific
        # value (if present) overrides the plain value.
        resolved_managed = bool(
            data.get(managed_keys.get(current_suffix) or managed_keys[""])
        )
        resolved_source_key = source_keys.get(current_suffix) or source_keys.get("")
        resolved_source = data.get(resolved_source_key) if resolved_source_key else None

        # Always-unmanaged marketplaces are forced off; a managed pack must have a
        # source; an unmanaged pack must not carry this marketplace's own source.
        if current_marketplace in ALWAYS_UNMANAGED_MARKETPLACES:
            resolved_managed = False
        elif resolved_managed and resolved_source is None:
            raise ValueError(
                f"Pack metadata is 'managed: true' for marketplace "
                f"'{current_marketplace.value}' but has no resolved 'source'. "
                f"A managed pack must define a 'source'."
            )
        elif not resolved_managed and source_keys.get(current_suffix):
            raise ValueError(
                f"Pack metadata has a 'source' for marketplace "
                f"'{current_marketplace.value}' but its resolved 'managed' is "
                f"false. A 'source' is only valid when managed is true."
            )

        # Collapse to the resolved plain values only.
        _remove_managed_and_source_keys(data)
        data[MANAGED_KEY] = resolved_managed
        if resolved_managed:
            data[SOURCE_KEY] = resolved_source

        return data
