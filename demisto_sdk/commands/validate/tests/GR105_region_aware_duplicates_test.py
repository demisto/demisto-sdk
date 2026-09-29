"""Region-awareness of the GR105 duplicate-ID rule.

A repeated (content type, id) is no longer an error on its own. It is an error
only when the two items are active in at least one common region. These tests
exercise `_colliding_regions` directly - the decision function the validator
applies to every pair the graph returns - so the matrix of cases can be covered
without standing up a Neo4j graph per case.
"""

import pytest

from demisto_sdk.commands.common.regional_rules import RegionalRules
from demisto_sdk.commands.common.tools import get_relative_path_from_packs_dir
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_integration_object,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR105_duplicate_content_id_all_files import (
    DuplicateContentIdValidatorAllFiles,
)
from TestSuite.test_tools import ChangeCWD

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
    """A stand-in carrying only what the collision check reads.

    The pack is exposed as `in_pack`, matching the accessor production code
    uses. Exposing a bare `pack` field instead would let the fake pass even if
    the resolver went back to reading that lazily-filled cache directly.
    """

    def __init__(
        self, supported_features=None, pack_features=None, path="Packs/P/x.yml"
    ):
        self.supportedFeatures = supported_features
        self.in_pack = FakePack(pack_features)
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


@pytest.mark.parametrize(
    "features_a, features_b, expected",
    [
        pytest.param([], [], {"us", "eu"}, id="empty list vs empty list"),
        pytest.param([], None, {"us", "eu"}, id="empty list vs absent key"),
        pytest.param([], ["feat_a"], {"us"}, id="empty list vs known feature"),
        pytest.param(
            [], ["feat_unknown"], set(), id="empty list vs unresolvable feature"
        ),
    ],
)
def test_empty_supported_features_is_treated_as_all_regions(
    features_a, features_b, expected
):
    """
    Given:
    - A pair in which one side declares `supportedFeatures: []`, paired with
      every kind of counterpart: another empty list, an absent key, a feature
      that resolves, and a feature that does not.

    When:
    - Determining the regions in which both are active.

    Then:
    - Ensure `[]` behaves exactly like an absent key, i.e. active in every
      region. The content owner's semantics are that an empty list expresses
      no restriction; resolving it to "no regions" would make an unrestricted
      item look region-limited and would push every such pair into the
      "regions could not be determined" branch with a backwards explanation.
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

    def test_identical_feature_names_omit_the_differing_names_note(self):
        """
        Given:
        - A colliding pair whose two items declare the very same feature.

        When:
        - Building the explanation.

        Then:
        - Ensure the "different feature names still collide" note is omitted.
          The note explains a subtlety that does not apply here - the names are
          identical - and printing it invites the author to look for a name
          mismatch that does not exist.
        """
        explanation = DuplicateContentIdValidatorAllFiles()._explain(
            FakeItem(["feat_a"]), FakeItem(["feat_a"]), {"us"}
        )

        assert "feat_a" in explanation
        assert "different feature names" not in explanation

    def test_only_the_unresolvable_feature_is_named(self):
        """
        Given:
        - A pair reported because its regions could not be resolved, where one
          item's feature resolves to a region and the other's does not.

        When:
        - Building the explanation.

        Then:
        - Ensure only the feature that actually failed to resolve is named.
          Listing the resolvable one too overstates the problem and sends the
          author hunting for a second, non-existent typo.
        """
        explanation = DuplicateContentIdValidatorAllFiles()._explain(
            FakeItem(["feat_unknown"], path="Packs/A/a.yml"),
            FakeItem(["feat_a"], path="Packs/B/b.yml"),
            set(),
            RULES,
        )

        assert "feat_unknown" in explanation
        assert "feat_a" not in explanation

    def test_the_rules_file_is_named_by_its_repo_relative_path(self):
        """
        Given:
        - A pair reported because its features could not be resolved.

        When:
        - Building the explanation, which points the author at the rules file.

        Then:
        - Ensure the rules file is named by its repo-relative path, with no
          parent directory prefixed. The absolute path is a CI checkout
          location (e.g. /builds/xdr/cortex-content/content/Config/...) that
          does not exist on the author's machine.
        """
        explanation = DuplicateContentIdValidatorAllFiles()._explain(
            FakeItem(["feat_unknown"]), FakeItem(["feat_unknown"]), set()
        )

        assert "Config/regional_rules.json" in explanation
        # Any directory prefix means a checkout-specific absolute path leaked.
        assert "/Config/regional_rules.json" not in explanation

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

    def test_explicit_empty_feature_list_reads_as_supported_everywhere(self):
        """
        Given:
        - One item declaring `supportedFeatures: []` and another declaring no
          `supportedFeatures` key at all.

        When:
        - Formatting each value for the error message.

        Then:
        - Ensure both render as supported everywhere. The two state the same
          thing - no restriction - so describing the empty list as "active in
          no region" would tell the author the opposite of what they wrote and
          contradict the region set it actually resolves to.
        """
        formatted_empty = DuplicateContentIdValidatorAllFiles()._fmt(frozenset())
        formatted_absent = DuplicateContentIdValidatorAllFiles()._fmt(None)

        assert formatted_empty == formatted_absent
        assert "supported everywhere" in formatted_empty


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


class TestReportedContentObject:
    """Each result must be attributed to the file its message was built from.

    Items in a duplicate-ID group share an `object_id` by definition, so any
    attribution keyed on the ID collapses the whole group onto one item and the
    reported file stops matching the message - it names the counterpart, making
    the error read as though a file duplicates itself.
    """

    def test_each_result_is_attributed_to_the_item_it_describes(self, mocker):
        """
        Given:
        - Two real content items sharing an ID and a region, so the pair
          genuinely collides.

        When:
        - Running the validator over the graph.

        Then:
        - Ensure each result is attributed to the item whose *counterpart* is
          named in its message. Attribution keyed on the shared object_id would
          collapse both results onto one item, and the reported file would then
          name itself as its own duplicate.
        """
        with ChangeCWD(REPO.path):
            item_a = create_integration_object(
                paths=["supportedFeatures"], values=[["feat_a"]]
            )
            item_b = create_integration_object(
                paths=["supportedFeatures"], values=[["feat_a"]]
            )

        validator = DuplicateContentIdValidatorAllFiles()
        mocker.patch.object(RegionalRules, "from_path", return_value=RULES)
        mocker.patch.object(
            type(validator),
            "graph",
            new_callable=mocker.PropertyMock,
            return_value=mocker.Mock(
                validate_duplicate_ids=mocker.Mock(
                    return_value=[(item_a, [item_b]), (item_b, [item_a])]
                )
            ),
        )

        results = validator.obtain_invalid_content_items_using_graph(
            [item_a, item_b], validate_all_files=True
        )

        assert len(results) == 2
        # Each result must be attributed to a different file...
        assert {str(result.content_object.path) for result in results} == {
            str(item_a.path),
            str(item_b.path),
        }
        # ...and never to the file its own message names as the duplicate.
        # Compared by repo-relative path, since the factory gives both items
        # the same file name under different pack directories.
        for result in results:
            reported = get_relative_path_from_packs_dir(str(result.content_object.path))
            assert reported not in result.message
