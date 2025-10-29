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
