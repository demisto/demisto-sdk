import pytest

from demisto_sdk.commands.common.regional_rules import RegionalRules
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_integration_object,
    create_playbook_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA134_unknown_supported_feature import (
    UnknownSupportedFeatureValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA135_redundant_supported_features import (
    RedundantSupportedFeaturesValidator,
)
from demisto_sdk.commands.validate.validators.ST_validators.ST115_is_supported_features_subset_of_pack import (
    IsSupportedFeaturesSubsetOfPack,
)
from TestSuite.test_tools import ChangeCWD

RULES = {
    "_meta": {"supported_features": "union"},
    "global": {"supported_features": ["feat_global"]},
    "us": {"supported_features": ["feat_a", "feat_b"]},
    "eu": {"supported_features": ["feat_e"]},
}


class TestIsSupportedFeaturesSubsetOfPack:
    def test_item_declares_feature_the_pack_lacks(self):
        """
        Given:
            - An integration whose 'supportedFeatures' includes a feature not allowed by its pack.
        When:
            - Running the IsSupportedFeaturesSubsetOfPack (ST115) validator.
        Then:
            - The validation should fail, naming the offending feature.
        """
        with ChangeCWD(REPO.path):
            integration = create_integration_object(
                paths=["supportedFeatures"],
                values=[["feat_a", "feat_c"]],
                pack_info={"supportedFeatures": ["feat_a", "feat_b"]},
            )

            results = IsSupportedFeaturesSubsetOfPack().obtain_invalid_content_items(
                [integration]
            )

            assert len(results) == 1
            assert "feat_c" in results[0].message
            assert "feat_a" not in results[0].message
            assert results[0].validator.error_code == "ST115"

    def test_item_is_a_subset_of_the_pack(self):
        """
        Given:
            - A script whose 'supportedFeatures' are a subset of its pack's.
        When:
            - Running the IsSupportedFeaturesSubsetOfPack (ST115) validator.
        Then:
            - The validation should pass.
        """
        with ChangeCWD(REPO.path):
            script = create_script_object(
                paths=["supportedFeatures"],
                values=[["feat_a"]],
                pack_info={"supportedFeatures": ["feat_a", "feat_b"]},
            )

            assert not IsSupportedFeaturesSubsetOfPack().obtain_invalid_content_items(
                [script]
            )

    def test_pack_declaring_nothing_allows_any_feature(self):
        """
        Given:
            - An integration declaring a feature, whose pack declares no 'supportedFeatures'.
        When:
            - Running the IsSupportedFeaturesSubsetOfPack (ST115) validator.
        Then:
            - The validation should pass. A pack with no declaration is supported
              everywhere and therefore places no restriction on its items, rather
              than acting as an empty allow-list.
        """
        with ChangeCWD(REPO.path):
            integration = create_integration_object(
                paths=["supportedFeatures"], values=[["feat_a"]]
            )
            integration.pack.supportedFeatures = None

            assert not IsSupportedFeaturesSubsetOfPack().obtain_invalid_content_items(
                [integration]
            )

    def test_item_declaring_nothing_inherits_the_pack(self):
        """
        Given:
            - A playbook with no 'supportedFeatures', whose pack declares some.
        When:
            - Running the IsSupportedFeaturesSubsetOfPack (ST115) validator.
        Then:
            - The validation should pass, since the item inherits the pack's value.
        """
        with ChangeCWD(REPO.path):
            playbook = create_playbook_object(
                pack_info={"supportedFeatures": ["feat_a"]}
            )
            playbook.supportedFeatures = None

            assert not IsSupportedFeaturesSubsetOfPack().obtain_invalid_content_items(
                [playbook]
            )


class TestUnknownSupportedFeature:
    @pytest.fixture(autouse=True)
    def _patch_rules(self, mocker):
        mocker.patch.object(
            RegionalRules, "from_path", return_value=RegionalRules(RULES)
        )

    @pytest.mark.parametrize(
        "item_features, should_fail",
        [
            pytest.param(["feat_a"], False, id="feature declared in a region"),
            pytest.param(["feat_global"], False, id="feature declared in global"),
            pytest.param(
                ["feat_a", "feat_e"], False, id="features from different regions"
            ),
            pytest.param(["feat_unknown"], True, id="feature declared nowhere"),
            pytest.param(
                ["feat_a", "feat_unknown"], True, id="one unknown among known features"
            ),
        ],
    )
    def test_known_features(self, item_features, should_fail):
        """
        Given:
            - An integration declaring features that do or do not exist under
              'supported_features' in Config/regional_rules.json.
        When:
            - Running the UnknownSupportedFeatureValidator (BA134).
        Then:
            - Only values absent from both 'global' and every region block are
              reported, since those can never be enabled anywhere.
        """
        with ChangeCWD(REPO.path):
            integration = create_integration_object(
                paths=["supportedFeatures"], values=[item_features]
            )

            results = UnknownSupportedFeatureValidator().obtain_invalid_content_items(
                [integration]
            )

            assert bool(results) is should_fail

    def test_message_names_offending_and_known_features(self):
        """
        Given:
            - An integration declaring a mistyped feature name.
        When:
            - Running the UnknownSupportedFeatureValidator (BA134).
        Then:
            - The message names both the offending value and the known features,
              so a typo is immediately obvious to the author.
        """
        with ChangeCWD(REPO.path):
            integration = create_integration_object(
                paths=["supportedFeatures"], values=[["feat_typo"]]
            )

            [result] = UnknownSupportedFeatureValidator().obtain_invalid_content_items(
                [integration]
            )

            assert "feat_typo" in result.message
            assert "feat_a" in result.message
            assert result.validator.error_code == "BA134"


def test_unknown_feature_skipped_when_regional_rules_absent(mocker):
    """
    Given:
        - No regional rules file, as on a contributor's pack-only checkout.
    When:
        - Running the UnknownSupportedFeatureValidator (BA134).
    Then:
        - No failure is reported. There is nothing to validate against, and
          failing here would block contributors who cannot see the config file.
    """
    mocker.patch.object(RegionalRules, "from_path", return_value=None)
    with ChangeCWD(REPO.path):
        integration = create_integration_object(
            paths=["supportedFeatures"], values=[["anything_at_all"]]
        )

        assert not UnknownSupportedFeatureValidator().obtain_invalid_content_items(
            [integration]
        )


class TestRedundantSupportedFeatures:
    def test_identical_to_pack_is_redundant(self):
        """
        Given:
            - An integration whose 'supportedFeatures' exactly matches its pack's.
        When:
            - Running the RedundantSupportedFeaturesValidator (BA135).
        Then:
            - A result is reported, since omitting the field would behave identically.
        """
        with ChangeCWD(REPO.path):
            integration = create_integration_object(
                paths=["supportedFeatures"],
                values=[["feat_a", "feat_b"]],
                pack_info={"supportedFeatures": ["feat_a", "feat_b"]},
            )

            results = (
                RedundantSupportedFeaturesValidator().obtain_invalid_content_items(
                    [integration]
                )
            )

            assert len(results) == 1
            assert results[0].validator.error_code == "BA135"

    def test_identical_ignoring_order_is_redundant(self):
        """
        Given:
            - An integration declaring its pack's features in a different order.
        When:
            - Running the RedundantSupportedFeaturesValidator (BA135).
        Then:
            - A result is reported. Order carries no meaning, so a reordered but
              equal list is still a redundant restatement of the pack's value.
        """
        with ChangeCWD(REPO.path):
            integration = create_integration_object(
                paths=["supportedFeatures"],
                values=[["feat_b", "feat_a"]],
                pack_info={"supportedFeatures": ["feat_a", "feat_b"]},
            )

            assert RedundantSupportedFeaturesValidator().obtain_invalid_content_items(
                [integration]
            )

    def test_strict_subset_is_not_redundant(self):
        """
        Given:
            - A script declaring a strict subset of its pack's features.
        When:
            - Running the RedundantSupportedFeaturesValidator (BA135).
        Then:
            - No result is reported, since the item genuinely narrows the pack's value.
        """
        with ChangeCWD(REPO.path):
            script = create_script_object(
                paths=["supportedFeatures"],
                values=[["feat_a"]],
                pack_info={"supportedFeatures": ["feat_a", "feat_b"]},
            )

            assert (
                not RedundantSupportedFeaturesValidator().obtain_invalid_content_items(
                    [script]
                )
            )

    def test_pack_declaring_nothing_is_not_redundant(self):
        """
        Given:
            - An integration declaring features, whose pack declares none.
        When:
            - Running the RedundantSupportedFeaturesValidator (BA135).
        Then:
            - No result is reported. The item restricts an otherwise unrestricted
              pack, which is meaningful rather than redundant.
        """
        with ChangeCWD(REPO.path):
            integration = create_integration_object(
                paths=["supportedFeatures"], values=[["feat_a"]]
            )
            integration.pack.supportedFeatures = None

            assert (
                not RedundantSupportedFeaturesValidator().obtain_invalid_content_items(
                    [integration]
                )
            )
