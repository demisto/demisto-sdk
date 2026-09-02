"""Region-awareness of the GR105 duplicate-ID rule.

A repeated (content type, id) is no longer an error on its own. It is an error
only when the two items are active in at least one common region. These tests
exercise `_colliding_regions` directly - the decision function the validator
applies to every pair the graph returns - so the matrix of cases can be covered
without standing up a Neo4j graph per case.
"""

import pytest

from demisto_sdk.commands.common.regional_rules import RegionalRules
from demisto_sdk.commands.validate.validators.GR_validators.GR105_duplicate_content_id_all_files import (
    DuplicateContentIdValidatorAllFiles,
)

RULES = RegionalRules(
    {
        "_meta": {"supported_features": "union"},
        "global": {"supported_features": ["feat_global"]},
        "us": {"supported_features": ["feat_a", "feat_b"]},
        "eu": {"supported_features": ["feat_e"]},
    }
)


class FakePack:
    def __init__(self, supported_features=None):
        self.supportedFeatures = supported_features


class FakeItem:
    """A stand-in carrying only what the collision check reads."""

    def __init__(
        self, supported_features=None, pack_features=None, path="Packs/P/x.yml"
    ):
        self.supportedFeatures = supported_features
        self.pack = FakePack(pack_features)
        self.path = path
        self.object_id = "SharedId"


def _collide(item_a, item_b, rules=RULES):
    return DuplicateContentIdValidatorAllFiles()._colliding_regions(
        item_a, item_b, rules
    )


@pytest.mark.parametrize(
    "features_a, features_b, expected",
    [
        pytest.param(["feat_a"], ["feat_a"], {"us"}, id="identical features collide"),
        pytest.param(
            ["feat_a"],
            ["feat_b"],
            {"us"},
            id="disjoint features mapped to the same region still collide",
        ),
        pytest.param(
            ["feat_a"], ["feat_e"], None, id="disjoint features in different regions"
        ),
        pytest.param(
            None, ["feat_a"], {"us"}, id="supported everywhere collides with restricted"
        ),
        pytest.param(
            None, None, {"us", "eu"}, id="two supported everywhere items collide"
        ),
        pytest.param(
            ["feat_a", "feat_e"],
            ["feat_e"],
            {"eu"},
            id="collision in only one of several active regions",
        ),
        pytest.param(
            ["feat_global"],
            ["feat_a"],
            {"us"},
            id="global feature is enabled everywhere so it collides",
        ),
    ],
)
def test_region_collision(features_a, features_b, expected):
    """
    Given:
    - Two content items sharing a content type and an ID, with the feature
      combinations that drive the duplicate rule.

    When:
    - Determining the regions in which both are active.

    Then:
    - Ensure a collision is reported exactly when the items share a region.
      Critically, disjoint feature *names* are not sufficient to avoid a
      duplicate: two different features mapped to the same region collide there.
    """
    assert _collide(FakeItem(features_a), FakeItem(features_b)) == expected


def test_features_inherited_from_the_pack_are_used():
    """
    Given:
    - Two items that declare nothing themselves, whose packs declare features
      mapped to different regions.

    When:
    - Determining whether they collide.

    Then:
    - Ensure the pack's value is used via the shared resolver, so the items do
      not collide. Comparing the raw item values would wrongly treat both as
      supported everywhere and report a false duplicate.
    """
    item_a = FakeItem(None, pack_features=["feat_a"])
    item_b = FakeItem(None, pack_features=["feat_e"])

    assert _collide(item_a, item_b) is None


def test_item_value_overrides_the_pack_value():
    """
    Given:
    - Two items whose packs would not collide, but where one item overrides its
      pack with a feature active in the other's region.

    When:
    - Determining whether they collide.

    Then:
    - Ensure the item's own value wins, producing a collision. The pack value
      must not be merged in, which would mask the conflict.
    """
    item_a = FakeItem(["feat_e"], pack_features=["feat_a"])
    item_b = FakeItem(None, pack_features=["feat_e"])

    assert _collide(item_a, item_b) == {"eu"}


class TestWithoutRegionalRules:
    """Behaviour when Config/regional_rules.json is unavailable.

    The features cannot be mapped to regions, so the check degrades to the
    weaker feature-name test. It never permits a genuine overlap, but it does
    permit two items whose distinct features share a region - that case can
    only be caught where the config file is present.
    """

    def test_shared_feature_name_still_collides(self):
        """
        Given:
        - No regional rules, and two items sharing a feature name.

        When:
        - Determining whether they collide.

        Then:
        - Ensure the collision is still reported.
        """
        assert _collide(FakeItem(["feat_a"]), FakeItem(["feat_a"]), rules=None)

    def test_supported_everywhere_still_collides(self):
        """
        Given:
        - No regional rules, and an item with no feature restriction.

        When:
        - Determining whether it collides with a restricted item.

        Then:
        - Ensure the collision is still reported, since an unrestricted item
          overlaps everything regardless of the region mapping.
        """
        assert _collide(FakeItem(None), FakeItem(["feat_a"]), rules=None) is not None

    def test_distinct_feature_names_are_permitted(self):
        """
        Given:
        - No regional rules, and two items with distinct feature names.

        When:
        - Determining whether they collide.

        Then:
        - Ensure no collision is reported. This is the documented limitation:
          without the config we cannot know the two features share a region.
        """
        assert _collide(FakeItem(["feat_a"]), FakeItem(["feat_b"]), rules=None) is None


class TestErrorMessage:
    def test_supported_everywhere_is_called_out(self):
        """
        Given:
        - A colliding pair in which one item declares no features.

        When:
        - Building the explanation.

        Then:
        - Ensure the message names the offending file and states that it is
          supported everywhere. This is the most common failure mode, so it must
          be explained rather than leaving the author to infer it.
        """
        explanation = DuplicateContentIdValidatorAllFiles()._explain(
            FakeItem(None, path="Packs/A/a.yml"),
            FakeItem(["feat_a"], path="Packs/B/b.yml"),
        )

        assert "a.yml" in explanation
        assert "supported everywhere" in explanation

    def test_overlapping_features_are_named(self):
        """
        Given:
        - A colliding pair where both items declare features.

        When:
        - Building the explanation.

        Then:
        - Ensure both feature values are named, and that the message warns that
          different feature names can still collide within one region.
        """
        explanation = DuplicateContentIdValidatorAllFiles()._explain(
            FakeItem(["feat_a"]), FakeItem(["feat_b"])
        )

        assert "feat_a" in explanation
        assert "feat_b" in explanation
        assert "same region" in explanation


class TestUnresolvableRegions:
    """A pair whose regions cannot be resolved must still be reported.

    Region-awareness may only ever excuse a duplicate ID that is *proven* not to
    overlap; when nothing can be proven, GR105 falls back to its original
    behaviour of reporting every duplicate.
    """

    def test_features_unknown_to_every_region_still_collide(self):
        """
        Given:
        - Two items declaring the same feature, which no region enables.

        When:
        - Determining whether they collide.

        Then:
        - Ensure the collision is reported. Neither item maps to a region, so
          non-overlap cannot be proven and the duplicate must not be excused.
        """
        assert (
            _collide(FakeItem(["feat_unknown"]), FakeItem(["feat_unknown"])) is not None
        )

    def test_unrestricted_items_collide_when_no_regions_are_declared(self):
        """
        Given:
        - A rules file declaring no region blocks, and two unrestricted items.

        When:
        - Determining whether they collide.

        Then:
        - Ensure the collision is reported, matching the behaviour before GR105
          became region-aware.
        """
        global_only = RegionalRules(
            {"_meta": {"supported_features": "union"}, "global": {}}
        )

        assert _collide(FakeItem(None), FakeItem(None), rules=global_only) is not None
