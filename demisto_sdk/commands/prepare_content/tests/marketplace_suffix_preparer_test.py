from copy import deepcopy

import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.prepare_content.preparers import (
    marketplace_suffix_preparer,
)
from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import (
    MarketplaceSuffixPreparer,
)

DATA = {
    "id": "Test",
    "id:xsoar": "xsoar",
    "name": "Test",
    "image": "testregular",
    "image:marketplacev2": "marketplacev2",
    "some": "some",
    "some:xpanse": "xpanse",
    "some:xsoar_on_prem": "xsoar_on_prem",
    "some:xsoar_saas": "xsoar_saas",
    "value": {"simple": "test value"},
    "value:xsoar": {"simple": "test xsoar value"},
    "value:marketplacev2": {"simple": "test marketplacev2 value"},
    "properties": {
        "ab": "test",
        "ab:xsoar": "xsoar",
        "cd": "test2",
        "cd:xpanse": "xpanse",
        "ef": "test3",
        "ef:xsoar_on_prem": "xsoar_on_prem",
        "gh": "test4",
        "gh:xsoar_saas": "xsoar_saas",
        "ij": "test5",
        "ij:marketplacev2": "marketplacev2",
        "ty:bla": "bla",
    },
    "inputs": {
        "description": "Test",
        "description:xsoar": "xsoar desc",
        "description:xpanse": "xpanse desc",
        "key": "some_key",
        "key:xsoar": "xsoar key",
        "required": False,
        "required:marketplacev2": True,
    },
    "1": {
        "id": "1",
        "task": {
            "loop": {
                "scriptId": "some script id",
                "scriptId:marketplacev2": "mv2 script id",
                "scriptArguments": "generic args",
                "scriptArguments:marketplacev2": "mv2 script args",
            }
        },
        "taskid": "some task id",
        "form": "general form",
        "form:marketplacev2": "mv2 form",
        "message": "general message",
        "message:marketplacev2": "mv2 message",
        "conditions": {
            "label": "yes",
            "condition": [
                {
                    "operator": "isEqualString",
                    "left": {"value": {"simple": "generic"}},
                    "left:xpanse": {"value": {"simple": "xpanse"}},
                    "right": {"value": {"simple": "generic"}},
                    "right:xpanse": {"value": {"simple": "xpanse"}},
                }
            ],
        },
        "scriptarguments": {"alert_id": {"simple": "11"}},
        "scriptarguments:xsoar_saas": {"alert_saas": {"simple": "saas"}},
        "scriptarguments:xpanse": {"alert_saas": {"simple": "xpanse args"}},
    },
    "1:xsoar": {"id": "1"},
}


def test_remove_xsoar():
    """
    Given:
        - data with suffixes for all marketplaces

    When:
        - Calling MarketplaceSuffixPreparer.prepare on the data when running on XSOAR marketplace

    Then:
        - The key is replaced by the XSOAR specific key
    """
    data = MarketplaceSuffixPreparer.prepare(deepcopy(DATA), MarketplaceVersions.XSOAR)
    assert data == {
        "id": "xsoar",
        "name": "Test",
        "image": "testregular",
        "some": "some",
        "value": {"simple": "test xsoar value"},
        "properties": {
            "ab": "xsoar",
            "cd": "test2",
            "ef": "test3",
            "gh": "test4",
            "ij": "test5",
            "ty:bla": "bla",
        },
        "1": {"id": "1"},
        "inputs": {
            "description": "xsoar desc",
            "key": "xsoar key",
            "required": False,
        },
    }


def test_remove_marketplacev2():
    """
    Given:
        - data with suffixes for all marketplaces

    When:
        - Calling MarketplaceSuffixPreparer.prepare on the data when running on XSIAM marketplace

    Then:
        - The key is replaced by the XSIAM specific key
    """
    data = MarketplaceSuffixPreparer.prepare(
        deepcopy(DATA), MarketplaceVersions.MarketplaceV2
    )
    assert data == {
        "id": "Test",
        "name": "Test",
        "image": "marketplacev2",
        "some": "some",
        "value": {"simple": "test marketplacev2 value"},
        "properties": {
            "ab": "test",
            "cd": "test2",
            "ef": "test3",
            "gh": "test4",
            "ij": "marketplacev2",
            "ty:bla": "bla",
        },
        "inputs": {
            "description": "Test",
            "key": "some_key",
            "required": True,
        },
        "1": {
            "id": "1",
            "task": {
                "loop": {
                    "scriptId": "mv2 script id",
                    "scriptArguments": "mv2 script args",
                }
            },
            "taskid": "some task id",
            "form": "mv2 form",
            "message": "mv2 message",
            "conditions": {
                "label": "yes",
                "condition": [
                    {
                        "operator": "isEqualString",
                        "left": {"value": {"simple": "generic"}},
                        "right": {"value": {"simple": "generic"}},
                    }
                ],
            },
            "scriptarguments": {"alert_id": {"simple": "11"}},
        },
    }


def test_remove_xpanse():
    """
    Given:
        - data with suffixes for all marketplaces

    When:
        - Calling MarketplaceSuffixPreparer.prepare on the data when running on XPANSE marketplace

    Then:
        - The key is replaced by the XSIAM specific key
    """
    data = MarketplaceSuffixPreparer.prepare(deepcopy(DATA), MarketplaceVersions.XPANSE)
    assert data == {
        "id": "Test",
        "name": "Test",
        "image": "testregular",
        "some": "xpanse",
        "value": {"simple": "test value"},
        "properties": {
            "ab": "test",
            "cd": "xpanse",
            "ef": "test3",
            "gh": "test4",
            "ij": "test5",
            "ty:bla": "bla",
        },
        "inputs": {
            "description": "xpanse desc",
            "key": "some_key",
            "required": False,
        },
        "1": {
            "id": "1",
            "task": {
                "loop": {
                    "scriptId": "some script id",
                    "scriptArguments": "generic args",
                }
            },
            "taskid": "some task id",
            "form": "general form",
            "message": "general message",
            "conditions": {
                "label": "yes",
                "condition": [
                    {
                        "operator": "isEqualString",
                        "left": {"value": {"simple": "xpanse"}},
                        "right": {"value": {"simple": "xpanse"}},
                    }
                ],
            },
            "scriptarguments": {"alert_saas": {"simple": "xpanse args"}},
        },
    }


def test_remove_xsoar_saas():
    """
    Given:
        - data with suffixes for all marketplaces

    When:
        - Calling MarketplaceSuffixPreparer.prepare on the data when running on XSOAR_SAAS marketplace

    Then:
        - The key is replaced by the XSOAR_SAAS specific key, or XSOAR if there is no XSOAR_SAAS key
    """
    data = MarketplaceSuffixPreparer.prepare(
        deepcopy(DATA), MarketplaceVersions.XSOAR_SAAS
    )
    assert data == {
        "id": "xsoar",
        "name": "Test",
        "image": "testregular",
        "some": "xsoar_saas",
        "value": {"simple": "test xsoar value"},
        "properties": {
            "ab": "xsoar",
            "cd": "test2",
            "ef": "test3",
            "gh": "xsoar_saas",
            "ij": "test5",
            "ty:bla": "bla",
        },
        "1": {"id": "1"},
        "inputs": {
            "description": "xsoar desc",
            "key": "xsoar key",
            "required": False,
        },
    }


class FakeMarketplaceVersions(StrEnum):
    """A copy of the real ``MarketplaceVersions`` enum with one extra, made-up
    marketplace (``testmp``) used only by the managed/source tests below.

    All real marketplaces are always-unmanaged except ``platform``, which leaves
    no second managed-able marketplace to exercise the suffix resolution rules
    against. Instead of misusing a real marketplace, we invent ``testmp``: it is
    not part of ``ALWAYS_UNMANAGED_MARKETPLACES``, so together with ``platform``
    the managed-able marketplaces are exactly ``['platform', 'testmp']``.
    """

    XSOAR = "xsoar"
    MarketplaceV2 = "marketplacev2"
    XPANSE = "xpanse"
    XSOAR_SAAS = "xsoar_saas"
    XSOAR_ON_PREM = "xsoar_on_prem"
    PLATFORM = "platform"
    TEST_MP = "testmp"


# The made-up marketplace used as the managed-able "this marketplace" in the
# tests below (alongside ``platform``).
MANAGED_TEST_MARKETPLACE = FakeMarketplaceVersions.TEST_MP


@pytest.fixture
def managed_source_marketplaces(monkeypatch):
    """Swaps in ``FakeMarketplaceVersions`` (which adds the made-up ``testmp``
    marketplace) for the duration of a test.

    ``prepare_managed_and_source`` reads the module-level ``MarketplaceVersions``
    at call time to compute the set of valid (managed-able) suffixes. Patching it
    to ``FakeMarketplaceVersions`` makes ``testmp`` a valid managed-able
    marketplace without touching the real enum or the production
    ``ALWAYS_UNMANAGED_MARKETPLACES`` list (``testmp`` simply is not in it).
    """
    monkeypatch.setattr(
        marketplace_suffix_preparer,
        "MarketplaceVersions",
        FakeMarketplaceVersions,
    )


MANAGED_SOURCE_VALID_CASES = [
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"name": "MyPack"},
        {"name": "MyPack"},
        id="no managed field",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"managed": True, "source": "https://example.com"},
        {"managed": True, "source": "https://example.com"},
        id="plain managed true + source",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"managed": False},
        {"managed": False},
        id="plain managed false, no source",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {
            "managed": False,
            "managed:testmp": True,
            "source": "plain-source",
            "source:testmp": "testmp-source",
        },
        {"managed": True, "source": "testmp-source"},
        id="suffixed managed+source override plain (matching mp)",
    ),
    pytest.param(
        FakeMarketplaceVersions.PLATFORM,
        {
            "managed": False,
            "managed:testmp": True,
            "source": "plain-source",
            "source:testmp": "testmp-source",
        },
        {"managed": False},
        id="suffixed data, non-matching mp falls back to plain (unmanaged)",
    ),
    pytest.param(
        FakeMarketplaceVersions.XSOAR,
        {"managed": True, "source": "https://example.com"},
        {"managed": False},
        id="always-unmanaged marketplace (xsoar)",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {
            "managed": True,
            "source": "https://example.com",
            "managed:testmp": None,
            "source:testmp": None,
        },
        {"managed": True, "source": "https://example.com"},
        id="none-valued suffixed keys are removed",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"managed": False, "source": "https://example.com"},
        {"managed": False},
        id="source with managed false",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"managed": False, "managed:testmp": True, "source": "plain-source"},
        {"managed": True, "source": "plain-source"},
        id="suffixed managed true (matching mp) + plain source only",
    ),
    pytest.param(
        FakeMarketplaceVersions.PLATFORM,
        {"managed": False, "managed:testmp": True, "source": "plain-source"},
        {"managed": False},
        id="non-matching mp, plain source without this-mp suffix",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"managed": True, "source": None, "source:testmp": "testmp-source"},
        {"managed": True, "source": "testmp-source"},
        id="None plain source (absent) + suffixed source",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"managed": True, "source": "plain-source"},
        {"managed": True, "source": "plain-source"},
        id="plain managed+source survive stripping",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"managed": True, "managed:testmp": False, "source": "plain-source"},
        {"managed": False},
        id="suffixed managed false override turns pack unmanaged for this mp",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {
            "managed": True,
            "source": "plain-source",
            "source:testmp": "testmp-source",
        },
        {"managed": True, "source": "testmp-source"},
        id="plain managed true + mp-suffixed source (mixed resolution)",
    ),
    pytest.param(
        FakeMarketplaceVersions.XSOAR,
        {"managed": True, "managed:testmp": True, "source": "plain-source"},
        {"managed": False},
        id="always-unmanaged mp wins over suffixed managed for another mp",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {
            "managed": True,
            "source": "plain-source",
            "source:platform": "platform-source",
        },
        {"managed": True, "source": "plain-source"},
        id="managed true, plain source + source for another mp (uses plain source)",
    ),
]


@pytest.mark.usefixtures("managed_source_marketplaces")
@pytest.mark.parametrize("marketplace, data, expected", MANAGED_SOURCE_VALID_CASES)
def test_prepare_managed_and_source_valid(marketplace, data, expected):
    """
    Given:
        - Pack metadata with managed/source fields (plain and/or suffixed).

    When:
        - Calling MarketplaceSuffixPreparer.prepare_managed_and_source for a
          specific marketplace.

    Then:
        - The managed/source fields are resolved into their final,
          marketplace-specific values.
    """
    result = MarketplaceSuffixPreparer.prepare_managed_and_source(
        deepcopy(data), marketplace
    )
    assert result == expected


MANAGED_SOURCE_INVALID_CASES = [
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"managed:testmp": True, "source:testmp": "testmp-source"},
        "Pack metadata has a marketplace-suffixed 'managed' field "
        "('managed:testmp') but is missing a plain 'managed' field. "
        "A plain 'managed' value is required as the default for all "
        "other marketplaces.",
        id="suffixed managed without plain managed",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"managed": True, "managed:notamarketplace": True},
        "Invalid marketplace suffix in pack metadata field "
        "'managed:notamarketplace'. The suffix must be one of: "
        "['platform', 'testmp'].",
        id="invalid marketplace suffix",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"managed": True, "managed:xsoar": False},
        "Invalid marketplace suffix in pack metadata field "
        "'managed:xsoar'. The suffix must be one of: "
        "['platform', 'testmp'].",
        id="always-unmanaged suffix on managed",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"managed": True},
        "Pack metadata is 'managed: true' for marketplace 'testmp' "
        "but has no resolved 'source'. A managed pack must define a 'source'.",
        id="managed true without any source",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"source": "https://example.com"},
        "Pack metadata has a 'source' field but no 'managed' field. "
        "A 'source' is only valid for a managed pack (managed: true).",
        id="source without any managed",
    ),
    pytest.param(
        FakeMarketplaceVersions.PLATFORM,
        {
            "managed": False,
            "managed:testmp": True,
            "source": "plain-source",
            "source:platform": "platform-source",
        },
        "Pack metadata has a 'source' for marketplace 'platform' but its "
        "resolved 'managed' is false. A 'source' is only valid when managed "
        "is true.",
        id="non-matching mp, source suffixed for this mp but managed false",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {
            "managed": None,
            "managed:testmp": True,
            "source:testmp": "testmp-source",
        },
        "Pack metadata has a marketplace-suffixed 'managed' field "
        "('managed:testmp') but is missing a plain 'managed' field. "
        "A plain 'managed' value is required as the default for all "
        "other marketplaces.",
        id="None plain managed (absent) + suffixed managed true",
    ),
    pytest.param(
        MANAGED_TEST_MARKETPLACE,
        {"managed": True, "source:platform": "platform-source"},
        "Pack metadata is 'managed: true' for marketplace 'testmp' "
        "but has no resolved 'source'. A managed pack must define a 'source'.",
        id="managed true, source only for another mp",
    ),
]


@pytest.mark.usefixtures("managed_source_marketplaces")
@pytest.mark.parametrize(
    "marketplace, data, expected_error", MANAGED_SOURCE_INVALID_CASES
)
def test_prepare_managed_and_source_invalid(marketplace, data, expected_error):
    """
    Given:
        - Pack metadata with an invalid managed/source combination.

    When:
        - Calling MarketplaceSuffixPreparer.prepare_managed_and_source for a
          specific marketplace.

    Then:
        - A ValueError is raised with the expected message.
    """
    with pytest.raises(ValueError) as exc_info:
        MarketplaceSuffixPreparer.prepare_managed_and_source(
            deepcopy(data), marketplace
        )
    assert str(exc_info.value) == expected_error


def test_remove_xsoar_on_prem():
    """
    Given:
        - data with suffixes for all marketplaces

    When:
        - Calling MarketplaceSuffixPreparer.prepare on the data when running on XSOAR_ON_PREM marketplace

    Then:
        - The key is replaced by the XSOAR_SAAS specific key, or XSOAR if there is no XSOAR_ON_PREM key
    """
    data = MarketplaceSuffixPreparer.prepare(
        deepcopy(DATA), MarketplaceVersions.XSOAR_ON_PREM
    )
    assert data == {
        "id": "xsoar",
        "name": "Test",
        "image": "testregular",
        "some": "xsoar_on_prem",
        "value": {"simple": "test xsoar value"},
        "properties": {
            "ab": "xsoar",
            "cd": "test2",
            "ef": "xsoar_on_prem",
            "gh": "test4",
            "ij": "test5",
            "ty:bla": "bla",
        },
        "1": {"id": "1"},
        "inputs": {
            "description": "xsoar desc",
            "key": "xsoar key",
            "required": False,
        },
    }
