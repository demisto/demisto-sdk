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

    The file lives in the content-private repo, so it is absent on GitHub-level
    runs such as the SDK's own build. Without it no feature can be mapped to a
    region, so the region-aware part is switched off entirely and GR105 behaves
    exactly as it did before it became region-aware: every duplicate ID is
    reported.
    """

    @pytest.mark.parametrize(
        "features_a, features_b",
        [
            pytest.param(["feat_a"], ["feat_a"], id="shared feature name"),
            pytest.param(None, ["feat_a"], id="one item supported everywhere"),
            pytest.param(["feat_a"], ["feat_e"], id="features of different regions"),
            pytest.param(["feat_a"], ["feat_b"], id="distinct feature names"),
        ],
    )
    def test_every_duplicate_is_reported(self, features_a, features_b):
        """
        Given:
        - No regional rules, and two items sharing an ID with any combination
          of supported features.

        When:
        - Determining whether they collide.

        Then:
        - Ensure the collision is reported regardless of the features, since
          non-overlap cannot be proven without the rules file.
        """
        assert (
            _collide(FakeItem(features_a), FakeItem(features_b), rules=None) is not None
        )


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
            {"us"},
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
            FakeItem(["feat_a"]), FakeItem(["feat_b"]), {"us"}
        )

        assert "feat_a" in explanation
        assert "feat_b" in explanation
        assert "same region" in explanation

    def test_colliding_regions_are_listed(self):
        """
        Given:
        - A pair proven to collide in two named regions.

        When:
        - Building the region clause of the error message.

        Then:
        - Ensure the regions are named, so the author knows where the conflict
          actually is.
        """
        clause = DuplicateContentIdValidatorAllFiles()._region_clause({"us", "eu"})

        assert "eu, us" in clause

    def test_unresolved_regions_are_not_described_as_all_regions(self):
        """
        Given:
        - A reported pair whose colliding regions could not be resolved, which
          the decision function signals with an empty set.

        When:
        - Building the region clause of the error message.

        Then:
        - Ensure it does not claim the items collide in "all regions". An empty
          set means the regions are unknown, which is the opposite of knowing
          they collide everywhere.
        """
        clause = DuplicateContentIdValidatorAllFiles()._region_clause(set())

        assert "all regions" not in clause
        assert "could not be determined" in clause

    def test_unresolved_regions_do_not_assert_an_overlap(self):
        """
        Given:
        - A pair reported only because its regions could not be resolved, both
          items declaring features that no region enables.

        When:
        - Building the explanation.

        Then:
        - Ensure it does not state that the features resolve to overlapping
          regions. No overlap was proven, and claiming one sends the author
          looking for a conflict that does not exist.
        """
        explanation = DuplicateContentIdValidatorAllFiles()._explain(
            FakeItem(["feat_unknown"]), FakeItem(["feat_unknown"]), set()
        )

        assert "overlapping regions" not in explanation
        assert "could not be resolved" in explanation

    def test_explicit_empty_feature_list_is_distinguished_from_an_absent_key(self):
        """
        Given:
        - One item declaring `supportedFeatures: []` and another declaring no
          `supportedFeatures` key at all.

        When:
        - Formatting each value for the error message.

        Then:
        - Ensure the two render differently. They mean opposite things - an
          empty list restricts the item to no region, while an absent key means
          supported everywhere - so rendering both as "none" misleads the author.
        """
        formatted_empty = DuplicateContentIdValidatorAllFiles()._fmt(frozenset())
        formatted_absent = DuplicateContentIdValidatorAllFiles()._fmt(None)

        assert formatted_empty != formatted_absent


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
