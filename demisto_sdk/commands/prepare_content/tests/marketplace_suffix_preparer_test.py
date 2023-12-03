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
    data = MarketplaceSuffixPreparer.prepare(DATA, MarketplaceVersions.XSOAR_ON_PREM)
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
