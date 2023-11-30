from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import (
    MarketplaceSuffixPreparer,
)

DATA = {
    "id": "Test",
    "id:xsoar": "TestXsoar",
    "name": "Test",
    "image": "testregular",
    "image:marketplacev2": "testimage",
    "some": "some",
    "some:xpanse": "testsome",
    "some:xsoar_on_prem": "testsome3",
    "some:xsoar_saas": "testsome4",
    "properties": {
        "ab": "test",
        "ab:xsoar": "testab",
        "cd": "test2",
        "cd:xpanse": "testcd",
        "ef": "test3",
        "ef:xsoar_on_prem": "testef",
        "gh": "test4",
        "gh:xsoar_saas": "testgh",
        "ij": "test5",
        "ij:marketplacev2": "testij",
    },
}


def test_remove_xsoar():
    data = MarketplaceSuffixPreparer.prepare(DATA, MarketplaceVersions.XSOAR)
    assert data == {
        "id": "TestXsoar",
        "name": "Test",
        "image": "testregular",
        "some": "some",
        "properties": {
            "ab": "testab",
            "cd": "test2",
            "ef": "test3",
            "gh": "test4",
            "ij": "test5",
        },
    }


def test_remove_marketplacev2():
    data = MarketplaceSuffixPreparer.prepare(DATA, MarketplaceVersions.MarketplaceV2)
    assert data == {
        "id": "Test",
        "name": "Test",
        "image": "testimage",
        "some": "some",
        "properties": {
            "ab": "test",
            "cd": "test2",
            "ef": "test3",
            "gh": "test4",
            "ij": "testij",
        },
    }


def test_remove_xpanse():
    data = MarketplaceSuffixPreparer.prepare(DATA, MarketplaceVersions.XPANSE)
    assert data == {
        "id": "Test",
        "name": "Test",
        "image": "testregular",
        "some": "testsome",
        "properties": {
            "ab": "test",
            "cd": "testcd",
            "ef": "test3",
            "gh": "test4",
            "ij": "test5",
        },
    }


def test_remove_xsoar_saas():
    data = MarketplaceSuffixPreparer.prepare(DATA, MarketplaceVersions.XSOAR_SAAS)
    assert data == {
        "id": "TestXsoar",
        "name": "Test",
        "image": "testregular",
        "some": "testsome4",
        "properties": {
            "ab": "testab",
            "cd": "test2",
            "ef": "test3",
            "gh": "testgh",
            "ij": "test5",
        },
    }


def test_remove_xsoar_on_prem():
    data = MarketplaceSuffixPreparer.prepare(DATA, MarketplaceVersions.XSOAR_ON_PREM)
    assert data == {
        "id": "TestXsoar",
        "name": "Test",
        "image": "testregular",
        "some": "testsome3",
        "properties": {
            "ab": "testab",
            "cd": "test2",
            "ef": "testef",
            "gh": "test4",
            "ij": "test5",
        },
    }
