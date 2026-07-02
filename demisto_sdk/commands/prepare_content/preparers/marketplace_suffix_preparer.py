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
    MarketplaceVersions.MarketplaceV2,
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
        ``source`` (str) according to the current marketplace.

        Resolution rules:

        - A suffixed key (e.g. ``managed:platform``) overrides the plain key for
          that specific marketplace. The plain key is the default for every
          marketplace that has no specific suffix.
        - For marketplaces in ``ALWAYS_UNMANAGED_MARKETPLACES`` the pack is forced
          to ``managed: false`` and ``source`` is removed, without any resolution.
        - When the resolved ``managed`` is ``False``, the ``source`` field is
          removed entirely.
        - When the resolved ``managed`` is ``True``, the resolved ``source`` (the
          suffixed value if present, otherwise the plain value) is kept.
        - All suffixed ``managed``/``source`` keys are removed from the output.
          Suffixes belonging to ``ALWAYS_UNMANAGED_MARKETPLACES`` are not valid
          for ``managed``/``source`` and are simply stripped (never resolved).

        Validation rules (raise ``ValueError``):

        - A suffix that is not a valid ``MarketplaceVersions`` value.
        - A suffixed ``managed`` without a plain ``managed`` default.
        - A ``source`` (plain or suffixed) without any ``managed`` at all.
        - A resolved ``managed: true`` without a resolved ``source``.
        - A resolved ``source`` while the resolved ``managed`` is ``false``.

        Args:
            data: The pack metadata dictionary.
            current_marketplace: The marketplace the pack is being prepared for.

        Returns:
            The (possibly modified) pack metadata dictionary.
        """
        valid_suffixes = {
            f"{SEPARATOR}{mp.value}"
            for mp in MarketplaceVersions
            if mp not in ALWAYS_UNMANAGED_MARKETPLACES
        }

        def collect_keys(field: str) -> dict:
            """Maps each set key of ``field`` to its suffix (``""`` for the plain
            key, e.g. ``:platform`` for a suffixed one).

            Keys whose value is ``None`` are treated as absent (they only exist
            because the model declares them). An invalid suffix raises.
            """
            collected: dict = {}
            for key in data:
                if data[key] is None:
                    continue
                if key == field:
                    collected[""] = key
                elif key.startswith(f"{field}{SEPARATOR}"):
                    suffix = key[len(field):]
                    if suffix not in valid_suffixes:
                        raise ValueError(
                            f"Invalid marketplace suffix in pack metadata field "
                            f"'{key}'. The suffix must be one of: "
                            f"{sorted(s.lstrip(SEPARATOR) for s in valid_suffixes)}."
                        )
                    collected[suffix] = key
            return collected

        def remove_managed_and_source_keys() -> None:
            """Removes every ``managed``/``source`` key from ``data`` - both the
            plain keys and any suffixed ones (including always-unmanaged and
            ``None``-valued keys). The resolved values are set back afterwards."""
            for key in list(data.keys()):
                for field in (MANAGED_KEY, SOURCE_KEY):
                    if key == field or key.startswith(f"{field}{SEPARATOR}"):
                        data.pop(key, None)
                        break

        managed_keys = collect_keys(MANAGED_KEY)
        source_keys = collect_keys(SOURCE_KEY)

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
            raise ValueError(
                "Pack metadata has a marketplace-suffixed 'managed' field but is "
                "missing a plain 'managed' field. A plain 'managed' value is "
                "required as the default for all other marketplaces."
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
        remove_managed_and_source_keys()
        data[MANAGED_KEY] = resolved_managed
        if resolved_managed:
            data[SOURCE_KEY] = resolved_source

        return data
