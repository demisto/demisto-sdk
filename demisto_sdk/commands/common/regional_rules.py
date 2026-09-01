"""Reader and merge logic for the repo-level ``Config/regional_rules.json``.

The file is the per-region source of truth for which platform features are
enabled. Its shape is::

    {
      "_meta":  {"<field>": "<strategy>", ...},
      "global": {"<field>": [...], ...},
      "<region>": {"<field>": [...], ...}
    }

``_meta`` declares a merge strategy per field, ``global`` holds the baseline
values, and every other top-level key is a region (exactly two lower-case
ASCII letters).

This module only *reads* the file and resolves effective values. Structural
validation of the file lives in
``demisto_sdk/scripts/validate_regional_rules.py`` and is intentionally kept
separate, so that consumers can rely on a validated file while the validator
itself can report every problem rather than failing on the first one.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Set

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger

REGIONAL_RULES_RELATIVE_PATH = Path("Config") / "regional_rules.json"
REGIONAL_RULES_PATH = CONTENT_PATH / REGIONAL_RULES_RELATIVE_PATH

META_KEY = "_meta"
GLOBAL_KEY = "global"
SUPPORTED_FEATURES_FIELD = "supported_features"

#: A region key is exactly two lower-case ASCII letters, e.g. ``us``, ``eu``.
REGION_KEY_PATTERN = re.compile(r"^[a-z]{2}$")


class MergeStrategy(str, Enum):
    """The only merge strategies the contract allows."""

    UNION = "union"
    GLOBAL_ONLY = "global_only"
    REGIONAL_FALLBACK = "regional_fallback"


#: Applied when a field has no explicit ``_meta`` entry. Note that a missing
#: ``_meta`` entry is itself a validation error, so this default only keeps
#: read-side behaviour predictable for files that skipped validation.
DEFAULT_STRATEGY = MergeStrategy.UNION


class RegionalRules:
    """Resolved view over ``Config/regional_rules.json``.

    Instances are cheap value objects over an already-parsed dict, so tests
    can build one directly without touching the filesystem.
    """

    def __init__(self, data: Dict) -> None:
        self._data = data
        self._meta: Dict[str, str] = data.get(META_KEY) or {}
        self._global: Dict[str, List[str]] = data.get(GLOBAL_KEY) or {}
        self._regions: Dict[str, Dict[str, List[str]]] = {
            key: value
            for key, value in data.items()
            if key not in (META_KEY, GLOBAL_KEY) and isinstance(value, dict)
        }

    @classmethod
    def from_path(cls, path: Path = REGIONAL_RULES_PATH) -> Optional["RegionalRules"]:
        """Loads the file, returning ``None`` when it is absent or unreadable.

        Returning ``None`` rather than raising lets consumers degrade
        gracefully: the SDK is frequently run outside the content repo (for
        example on a contributor's pack-only checkout), where the file simply
        does not exist and its absence is not an error.
        """
        if not path.exists():
            logger.debug(f"No regional rules file at {path}")
            return None
        try:
            return cls(json.loads(path.read_text()))
        except Exception as error:
            # A malformed file is reported by the dedicated validator; here we
            # must not take down every unrelated command that reads it.
            logger.warning(f"Could not read regional rules from {path}: {error}")
            return None

    @property
    def regions(self) -> List[str]:
        """The region keys declared in the file, excluding ``_meta``/``global``."""
        return sorted(self._regions)

    def strategy(self, field: str) -> MergeStrategy:
        """The merge strategy for ``field``, falling back to the default."""
        try:
            return MergeStrategy(self._meta.get(field, DEFAULT_STRATEGY.value))
        except ValueError:
            # Unknown strategies are a validation error; be permissive on read.
            logger.warning(
                f"Unknown merge strategy {self._meta.get(field)!r} for field {field!r}, "
                f"falling back to {DEFAULT_STRATEGY.value}"
            )
            return DEFAULT_STRATEGY

    def effective_values(self, field: str, region: str) -> List[str]:
        """Resolves ``field`` for ``region`` according to its merge strategy.

        An explicitly authored empty list is an intentional empty value and is
        preserved as such; it is deliberately distinguished from an absent key.
        """
        global_value = self._global.get(field)
        region_block = self._regions.get(region, {})
        strategy = self.strategy(field)

        if strategy is MergeStrategy.GLOBAL_ONLY:
            # The region block is ignored entirely - its presence there is a
            # validation error, not something to merge in.
            return list(global_value or [])

        if strategy is MergeStrategy.REGIONAL_FALLBACK:
            # `in` rather than truthiness, so an explicit [] wins over global.
            if field in region_block:
                return list(region_block[field] or [])
            return list(global_value or [])

        # UNION: global values apply to every region, plus the region's own.
        merged = list(global_value or [])
        for value in region_block.get(field) or []:
            if value not in merged:
                merged.append(value)
        return merged

    def supported_features(self, region: str) -> Set[str]:
        """The features enabled in ``region``."""
        return set(self.effective_values(SUPPORTED_FEATURES_FIELD, region))

    def all_supported_features(self) -> Set[str]:
        """Every feature named anywhere in the file - ``global`` and all regions.

        This is the set a content item's declared feature must belong to; a
        value outside it does not exist as far as the platform is concerned.
        """
        features: Set[str] = set(self._global.get(SUPPORTED_FEATURES_FIELD) or [])
        for region_block in self._regions.values():
            features.update(region_block.get(SUPPORTED_FEATURES_FIELD) or [])
        return features

    def regions_enabling(self, feature: str) -> Set[str]:
        """The regions in which ``feature`` is enabled."""
        return {
            region
            for region in self._regions
            if feature in self.supported_features(region)
        }

    def regions_for_features(self, features: Optional[FrozenSet[str]]) -> Set[str]:
        """The regions an item is active in, given its resolved features.

        Uses UNION / ANY semantics: an item declaring ``["a", "b"]`` where
        ``a`` is enabled in ``us`` and ``b`` in ``eu`` is active in *both*.

        ``None`` means "supported everywhere" - the item carries no feature
        restriction at all - and therefore maps to every declared region. Note
        that this is distinct from an empty set, which would mean the item
        declared features that no region enables.

        This is the single place the ANY-vs-ALL rule is expressed; every
        consumer must go through here rather than reimplementing it.
        """
        if features is None:
            return set(self._regions)
        regions: Set[str] = set()
        for feature in features:
            regions |= self.regions_enabling(feature)
        return regions
