from pathlib import Path

import pytest

from demisto_sdk.commands.common.regional_rules import (
    MergeStrategy,
    RegionalRules,
)

SAMPLE = {
    "_meta": {
        "supported_features": "union",
        "trusted_platform_scripts": "global_only",
    },
    "global": {
        "supported_features": ["feat_global"],
        "trusted_platform_scripts": ["script_a"],
    },
    "us": {"supported_features": ["feat_a", "feat_b"]},
    "eu": {"supported_features": ["feat_e"]},
}


class TestRegionalRulesParsing:
    def test_regions_excludes_meta_and_global(self):
        """
        Given:
        - A regional rules file with `_meta`, `global` and two region blocks

        When:
        - Reading the declared regions

        Then:
        - Ensure only the region keys are returned, sorted, with `_meta` and
          `global` excluded
        """
        assert RegionalRules(SAMPLE).regions == ["eu", "us"]

    def test_strategy_defaults_to_union_when_not_declared(self):
        """
        Given:
        - A field with no `_meta` entry

        When:
        - Reading its merge strategy

        Then:
        - Ensure it falls back to union rather than raising
        """
        assert RegionalRules(SAMPLE).strategy("undeclared") is MergeStrategy.UNION

    def test_unknown_strategy_falls_back_to_union(self):
        """
        Given:
        - A `_meta` entry naming a strategy that does not exist

        When:
        - Reading the strategy

        Then:
        - Ensure the read path degrades to union instead of raising, leaving
          the failure to be reported by the dedicated file validator
        """
        rules = RegionalRules({"_meta": {"f": "not_a_strategy"}, "global": {}})
        assert rules.strategy("f") is MergeStrategy.UNION

    def test_from_path_returns_none_when_file_absent(self, tmp_path: Path):
        """
        Given:
        - A path with no regional rules file, as on a pack-only checkout

        When:
        - Loading the rules

        Then:
        - Ensure None is returned so consumers can degrade gracefully
        """
        assert RegionalRules.from_path(tmp_path / "missing.json") is None

    def test_from_path_returns_none_on_invalid_json(self, tmp_path: Path):
        """
        Given:
        - A regional rules file that does not parse

        When:
        - Loading the rules

        Then:
        - Ensure None is returned rather than an exception propagating into
          unrelated commands
        """
        path = tmp_path / "regional_rules.json"
        path.write_text("{not json")
        assert RegionalRules.from_path(path) is None


class TestMergeStrategies:
    def test_union_combines_global_and_region(self):
        """
        Given:
        - A union field with values in both `global` and a region block

        When:
        - Resolving the field for that region

        Then:
        - Ensure the result is the union of both
        """
        assert RegionalRules(SAMPLE).supported_features("us") == {
            "feat_global",
            "feat_a",
            "feat_b",
        }

    def test_global_only_ignores_region_block(self):
        """
        Given:
        - A global_only field that also (invalidly) appears in a region block

        When:
        - Resolving the field for that region

        Then:
        - Ensure only the global value is used and the region block is ignored
        """
        data = {
            "_meta": {"trusted_platform_scripts": "global_only"},
            "global": {"trusted_platform_scripts": ["script_a"]},
            "us": {"trusted_platform_scripts": ["script_regional"]},
        }
        resolved = RegionalRules(data).effective_values(
            "trusted_platform_scripts", "us"
        )
        assert resolved == ["script_a"]

    def test_regional_fallback_prefers_region_value(self):
        """
        Given:
        - A regional_fallback field present in the region block

        When:
        - Resolving the field

        Then:
        - Ensure the regional value replaces the global one rather than
          merging with it
        """
        data = {
            "_meta": {"f": "regional_fallback"},
            "global": {"f": ["global_value"]},
            "us": {"f": ["regional_value"]},
        }
        assert RegionalRules(data).effective_values("f", "us") == ["regional_value"]

    def test_regional_fallback_honours_explicit_empty_list(self):
        """
        Given:
        - A regional_fallback field explicitly set to [] in the region block

        When:
        - Resolving the field

        Then:
        - Ensure the empty list is treated as an intentional value and does
          not fall back to global, since [] differs from an absent key
        """
        data = {
            "_meta": {"f": "regional_fallback"},
            "global": {"f": ["global_value"]},
            "us": {"f": []},
        }
        assert RegionalRules(data).effective_values("f", "us") == []

    def test_regional_fallback_uses_global_when_key_absent(self):
        """
        Given:
        - A regional_fallback field absent from the region block

        When:
        - Resolving the field

        Then:
        - Ensure the global value is used
        """
        data = {
            "_meta": {"f": "regional_fallback"},
            "global": {"f": ["global_value"]},
            "us": {},
        }
        assert RegionalRules(data).effective_values("f", "us") == ["global_value"]


class TestFeatureLookup:
    def test_all_supported_features_spans_global_and_regions(self):
        """
        Given:
        - Features declared in `global` and across several region blocks

        When:
        - Collecting every known feature

        Then:
        - Ensure the union across all blocks is returned, which is the set an
          item's declared feature must belong to
        """
        assert RegionalRules(SAMPLE).all_supported_features() == {
            "feat_global",
            "feat_a",
            "feat_b",
            "feat_e",
        }

    def test_global_feature_is_enabled_in_every_region(self):
        """
        Given:
        - A feature declared only under `global` for a union field

        When:
        - Finding the regions that enable it

        Then:
        - Ensure every region is returned, since union means global applies
          everywhere
        """
        assert RegionalRules(SAMPLE).regions_enabling("feat_global") == {"us", "eu"}

    def test_regional_feature_is_enabled_only_in_its_region(self):
        """
        Given:
        - A feature declared in a single region block

        When:
        - Finding the regions that enable it

        Then:
        - Ensure only that region is returned
        """
        assert RegionalRules(SAMPLE).regions_enabling("feat_e") == {"eu"}


class TestRegionActivation:
    def test_supported_everywhere_maps_to_all_regions(self):
        """
        Given:
        - An item with no feature restriction at all (supported everywhere)

        When:
        - Computing its region activation

        Then:
        - Ensure it is active in every declared region
        """
        assert RegionalRules(SAMPLE).regions_for_features(None) == {"us", "eu"}

    def test_multiple_features_union_their_regions(self):
        """
        Given:
        - An item declaring two features mapped to different regions

        When:
        - Computing its region activation

        Then:
        - Ensure ANY/union semantics apply, so the item is active in both
          regions rather than only where both features are enabled
        """
        rules = RegionalRules(SAMPLE)
        assert rules.regions_for_features(frozenset({"feat_a", "feat_e"})) == {
            "us",
            "eu",
        }

    def test_unknown_feature_activates_nowhere(self):
        """
        Given:
        - An item declaring a feature no region enables

        When:
        - Computing its region activation

        Then:
        - Ensure the empty set is returned, which is distinct from the
          supported-everywhere case
        """
        assert RegionalRules(SAMPLE).regions_for_features(frozenset({"nope"})) == set()

    @pytest.mark.parametrize(
        "features_a, features_b, expected_collision",
        [
            pytest.param(
                frozenset({"feat_a"}),
                frozenset({"feat_a"}),
                {"us"},
                id="identical features collide",
            ),
            pytest.param(
                frozenset({"feat_a"}),
                frozenset({"feat_b"}),
                {"us"},
                id="disjoint features mapped to the same region still collide",
            ),
            pytest.param(
                frozenset({"feat_a"}),
                frozenset({"feat_e"}),
                set(),
                id="disjoint features in different regions do not collide",
            ),
            pytest.param(
                None,
                frozenset({"feat_a"}),
                {"us"},
                id="supported everywhere collides with a restricted item",
            ),
            pytest.param(
                None,
                None,
                {"us", "eu"},
                id="two supported everywhere items collide",
            ),
            pytest.param(
                frozenset({"feat_a", "feat_e"}),
                frozenset({"feat_e"}),
                {"eu"},
                id="collision in only one of several active regions",
            ),
        ],
    )
    def test_region_collision_matrix(self, features_a, features_b, expected_collision):
        """
        Given:
        - Two content items sharing a content type and id, with the feature
          combinations that drive the duplicate-ID rule

        When:
        - Intersecting their region activation sets

        Then:
        - Ensure the collision is detected exactly when both items are active
          in at least one common region. Notably, disjoint feature names are
          not sufficient to avoid a duplicate: two different features mapped
          to the same region still collide there.
        """
        rules = RegionalRules(SAMPLE)
        collision = rules.regions_for_features(features_a) & rules.regions_for_features(
            features_b
        )
        assert collision == expected_collision
