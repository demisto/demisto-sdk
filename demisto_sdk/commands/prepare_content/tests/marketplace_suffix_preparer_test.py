from copy import deepcopy

from demisto_sdk.commands.common.constants import MarketplaceVersions
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
    },
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
        "properties": {
            "ab": "xsoar",
            "cd": "test2",
            "ef": "test3",
            "gh": "test4",
            "ij": "test5",
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
        "properties": {
            "ab": "test",
            "cd": "test2",
            "ef": "test3",
            "gh": "test4",
            "ij": "marketplacev2",
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
        "properties": {
            "ab": "test",
            "cd": "xpanse",
            "ef": "test3",
            "gh": "test4",
            "ij": "test5",
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
        "properties": {
            "ab": "xsoar",
            "cd": "test2",
            "ef": "test3",
            "gh": "xsoar_saas",
            "ij": "test5",
        },
    }


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
        "properties": {
            "ab": "xsoar",
            "cd": "test2",
            "ef": "xsoar_on_prem",
            "gh": "test4",
            "ij": "test5",
        },
    }
