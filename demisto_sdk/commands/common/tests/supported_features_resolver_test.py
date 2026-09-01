import pytest

from demisto_sdk.commands.common.tools import get_content_item_supported_features


class FakePack:
    """Stands in for a Pack model, which the resolver special-cases."""

    def __init__(self, supported_features=None):
        self.supportedFeatures = supported_features


class FakeItem:
    def __init__(self, supported_features=None, pack=None):
        self.supportedFeatures = supported_features
        self.pack = pack


@pytest.mark.parametrize(
    "item_features, pack_features, expected",
    [
        pytest.param(
            ["feat_a"],
            ["feat_b"],
            frozenset({"feat_a"}),
            id="item value overrides the pack value entirely",
        ),
        pytest.param(
            ["feat_a"],
            None,
            frozenset({"feat_a"}),
            id="item value used when pack declares nothing",
        ),
        pytest.param(
            None,
            ["feat_b"],
            frozenset({"feat_b"}),
            id="pack value inherited when item declares nothing",
        ),
        pytest.param(
            None,
            None,
            None,
            id="supported everywhere when neither declares a value",
        ),
    ],
)
def test_resolution_hierarchy(item_features, pack_features, expected):
    """
    Given:
    - A content item and its pack, in every combination of declaring and not
      declaring `supportedFeatures`

    When:
    - Resolving the item's effective features

    Then:
    - Ensure the item's value wins outright when present, the pack's value is
      inherited only in its absence, and the values are never merged
    """
    item = FakeItem(item_features, pack=FakePack(pack_features))
    assert get_content_item_supported_features(item) == expected


def test_item_value_is_not_merged_with_pack_value():
    """
    Given:
    - An item and a pack that both declare different features

    When:
    - Resolving the item's effective features

    Then:
    - Ensure the pack's feature is absent from the result, proving the item's
      value is an override rather than a union
    """
    item = FakeItem(["feat_a"], pack=FakePack(["feat_b"]))
    assert get_content_item_supported_features(item) == frozenset({"feat_a"})


def test_supported_everywhere_is_distinct_from_empty_list():
    """
    Given:
    - One item resolving to supported everywhere, and one declaring []

    When:
    - Resolving both

    Then:
    - Ensure supported everywhere is None while the explicit empty list is an
      empty frozenset. Both are falsy, so consumers must branch on `is None`;
      conflating them would make an unrestricted item look restricted.
    """
    unrestricted = get_content_item_supported_features(
        FakeItem(None, pack=FakePack(None))
    )
    explicitly_empty = get_content_item_supported_features(
        FakeItem([], pack=FakePack(None))
    )

    assert unrestricted is None
    assert explicitly_empty == frozenset()
    assert unrestricted != explicitly_empty


def test_item_without_pack_falls_back_to_supported_everywhere():
    """
    Given:
    - An item with no pack association and no declared features

    When:
    - Resolving its features

    Then:
    - Ensure it resolves to supported everywhere rather than raising
    """
    assert get_content_item_supported_features(FakeItem(None, pack=None)) is None
