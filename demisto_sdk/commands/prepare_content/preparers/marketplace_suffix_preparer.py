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



if __name__ == "__main__":
    import copy
    import json

    def run_case(
        title: str,
        data: dict,
        current_marketplace: MarketplaceVersions,
    ) -> None:
        """Runs a single edge case and prints the input, marketplace and output.

        Any raised exception is caught and printed so all the cases run even if
        one of them fails (e.g. the deliberately invalid ones).
        """
        print("=" * 80)
        print(f"CASE: {title}")
        print(f"marketplace : {current_marketplace.value}")
        print(f"input       : {json.dumps(data, default=str)}")
        try:
            # deepcopy so the original input stays intact for printing/reuse
            result = MarketplaceSuffixPreparer.prepare_managed_and_source(
                copy.deepcopy(data), current_marketplace
            )
            print(f"output      : {json.dumps(result, default=str)}")
        except Exception as exc:  # noqa: BLE001 - we want to show any failure
            print(f"raised      : {type(exc).__name__}: {exc}")
        print()

    # ------------------------------------------------------------------ VALID

    # 1. No managed field at all - returned unchanged (pack is not managed).
    run_case(
        "no managed field",
        {"name": "MyPack"},
        MarketplaceVersions.MarketplaceV2,
    )

    # 2. Plain managed: True with a plain source - both kept.
    run_case(
        "plain managed true + source",
        {"managed": True, "source": "https://example.com"},
        MarketplaceVersions.MarketplaceV2,
    )

    # 3. Plain managed: False (no source) - source stays absent.
    run_case(
        "plain managed false, no source",
        {"managed": False},
        MarketplaceVersions.MarketplaceV2,
    )

    # 4. Suffixed managed+source override the plain values for the matching mp.
    run_case(
        "suffixed managed+source override plain (matching mp)",
        {
            "managed": False,
            "managed:marketplacev2": True,
            "source": "plain-source",
            "source:marketplacev2": "v2-source",
        },
        MarketplaceVersions.MarketplaceV2,
    )

    # 5. Same data, non-matching (non-always-unmanaged) mp - falls back to plain.
    #    Plain managed is False and there is no plain source, so it is unmanaged.
    run_case(
        "suffixed data, non-matching mp falls back to plain (unmanaged)",
        {
            "managed": False,
            "managed:marketplacev2": True,
            "source": "plain-source",
            "source:marketplacev2": "v2-source",
        },
        MarketplaceVersions.PLATFORM,
    )

    # 6. ALWAYS_UNMANAGED marketplace forces managed:false and drops source.
    run_case(
        "always-unmanaged marketplace (xsoar)",
        {"managed": True, "source": "https://example.com"},
        MarketplaceVersions.XSOAR,
    )

    # 7. None-valued suffixed keys (model-declared but unset) are cleaned up.
    run_case(
        "none-valued suffixed keys are removed",
        {
            "managed": True,
            "source": "https://example.com",
            "managed:marketplacev2": None,
            "source:marketplacev2": None,
        },
        MarketplaceVersions.MarketplaceV2,
    )

    # ---------------------------------------------------------------- INVALID

    # 8. Suffixed managed without a plain managed - ValueError.
    run_case(
        "suffixed managed without plain managed (invalid)",
        {"managed:marketplacev2": True, "source:marketplacev2": "v2-source"},
        MarketplaceVersions.MarketplaceV2,
    )

    # 9. Invalid marketplace suffix - ValueError.
    run_case(
        "invalid marketplace suffix (invalid)",
        {"managed": True, "managed:notamarketplace": True},
        MarketplaceVersions.MarketplaceV2,
    )

    # 10. Always-unmanaged suffix is not a valid managed/source suffix - ValueError.
    run_case(
        "always-unmanaged suffix on managed (invalid)",
        {"managed": True, "managed:xsoar": False},
        MarketplaceVersions.MarketplaceV2,
    )

    # 11. managed: true but no source at all - ValueError.
    run_case(
        "managed true without any source (invalid)",
        {"managed": True},
        MarketplaceVersions.MarketplaceV2,
    )

    # 12. source present while resolved managed is false - ValueError.
    run_case(
        "source with managed false (invalid)",
        {"managed": False, "source": "https://example.com"},
        MarketplaceVersions.MarketplaceV2,
    )

    # 13. source present with no managed field at all - ValueError.
    run_case(
        "source without any managed (invalid)",
        {"source": "https://example.com"},
        MarketplaceVersions.MarketplaceV2,
    )

    # ----------------------------------------------- THE CASE YOU WANTED TO ALLOW

    # 14. Suffixed managed:true for the current mp with only a PLAIN source (no
    #     source suffix). This is the case you said must be VALID.
    #     Expected: {"managed": true, "source": "plain-source"}.
    run_case(
        "suffixed managed true (matching mp) + plain source only (should be VALID)",
        {
            "managed": False,
            "managed:marketplacev2": True,
            "source": "plain-source",
        },
        MarketplaceVersions.MarketplaceV2,
    )

    # 15. Same data, a NON-matching mp. Plain managed is False and there is a
    #     plain source but NO source:<this-mp> suffix, so per your new rule this
    #     should be VALID (unmanaged, source dropped) - the plain source is only
    #     forbidden when it carries THIS marketplace's specific suffix.
    #     Expected: {"managed": false}.
    run_case(
        "non-matching mp, plain source without this-mp suffix (should be VALID)",
        {
            "managed": False,
            "managed:marketplacev2": True,
            "source": "plain-source",
        },
        MarketplaceVersions.PLATFORM,
    )

    # 16. Non-matching mp but with a source suffix FOR this mp while its resolved
    #     managed is false - THIS is the only source case that should be INVALID.
    #     Expected: ValueError.
    run_case(
        "non-matching mp, source suffixed for this mp but managed false (INVALID)",
        {
            "managed": False,
            "managed:marketplacev2": True,
            "source": "plain-source",
            "source:platform": "platform-source",
        },
        MarketplaceVersions.PLATFORM,
    )

    # ----------------------------------------------------- None-VALUE HANDLING

    # 17. None-valued PLAIN managed + a real suffixed managed:true. Since a None
    #     plain value is treated as ABSENT, this is a suffixed managed without a
    #     plain default -> ValueError (correct per the rules).
    run_case(
        "None plain managed (absent) + suffixed managed true (invalid)",
        {
            "managed": None,
            "managed:marketplacev2": True,
            "source:marketplacev2": "v2-source",
        },
        MarketplaceVersions.MarketplaceV2,
    )

    # 18. None-valued plain source + a real source suffix. The None plain source
    #     is treated as absent, so the suffixed value is used.
    #     Expected: {"managed": true, "source": "v2-source"}.
    run_case(
        "None plain source (absent) + suffixed source (uses suffixed value)",
        {
            "managed": True,
            "source": None,
            "source:marketplacev2": "v2-source",
        },
        MarketplaceVersions.MarketplaceV2,
    )

    # 19. Plain managed+source only: confirm the plain keys survive the stripping
    #     step and are returned as-is.
    #     Expected: {"managed": true, "source": "plain-source"}.
    run_case(
        "plain managed+source survive stripping",
        {"managed": True, "source": "plain-source"},
        MarketplaceVersions.MarketplaceV2,
    )

    # 20. Extra coverage: suffixed managed:false override that turns an otherwise
    #     managed pack OFF for the specific mp. Plain managed true + plain source,
    #     but managed:marketplacev2 false -> unmanaged for v2, source dropped.
    #     Expected: {"managed": false}.
    run_case(
        "suffixed managed false override turns pack unmanaged for this mp",
        {
            "managed": True,
            "managed:marketplacev2": False,
            "source": "plain-source",
        },
        MarketplaceVersions.MarketplaceV2,
    )

    # 21. Extra coverage: managed true resolved from PLAIN, source resolved from
    #     the mp-specific suffix (mixed resolution).
    #     Expected: {"managed": true, "source": "v2-source"}.
    run_case(
        "plain managed true + mp-suffixed source (mixed resolution)",
        {
            "managed": True,
            "source": "plain-source",
            "source:marketplacev2": "v2-source",
        },
        MarketplaceVersions.MarketplaceV2,
    )

    # 22. Extra coverage: always-unmanaged mp with suffixed managed for another
    #     mp - the always-unmanaged rule wins, everything is forced off.
    #     Expected: {"managed": false}.
    run_case(
        "always-unmanaged mp wins over suffixed managed for another mp",
        {
            "managed": True,
            "managed:marketplacev2": True,
            "source": "plain-source",
        },
        MarketplaceVersions.XSOAR,
    )

    # 23. New edge case: managed:true with a source suffix for ANOTHER mp only
    #     (no plain source, no source for this mp). The other-mp source is
    #     irrelevant here, so there is no resolved source -> ValueError.
    run_case(
        "managed true, source only for another mp (invalid - no source for this mp)",
        {
            "managed": True,
            "source:platform": "platform-source",
        },
        MarketplaceVersions.MarketplaceV2,
    )

    # 24. New edge case: managed:true with a plain source AND a source suffix for
    #     ANOTHER mp. The other-mp suffix is stripped; the plain source is used.
    #     Expected: {"managed": true, "source": "plain-source"}.
    run_case(
        "managed true, plain source + source for another mp (uses plain source)",
        {
            "managed": True,
            "source": "plain-source",
            "source:platform": "platform-source",
        },
        MarketplaceVersions.MarketplaceV2,
    )
