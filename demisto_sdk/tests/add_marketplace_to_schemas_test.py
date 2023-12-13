import demisto_sdk.scripts.add_marketplace_to_schemas as add_marketplace_to_schemas
from demisto_sdk.scripts.add_marketplace_to_schemas import add_key


def test_add_key(mocker):
    """
    Given:
        A nested mapping with some keys in NON_SUPPORTED_KEYS and some in SUPPORTED_KEYS

    When:
        Calling add_key(mapping) on the provided mapping to add the marketplaces regex

    Then:
        Assert that the mapping was modified as expected with the new regex keys added

    """
    mocker.patch.object(add_marketplace_to_schemas, "NON_SUPPORTED_KEYS", ["id"])
    mocker.patch.object(
        add_marketplace_to_schemas, "SUPPORTED_KEYS", ["isfetch", "mode"]
    )

    mapping = {
        "id": {"type": "string"},
        "isfetch": {"type": "string"},
        "map": {
            "type": "map",
            "mapping": {"key": {"type": "string"}, "mode": {"type": "string"}},
        },
    }
    add_key(mapping)
    assert mapping == {
        "id": {"type": "string"},
        "isfetch": {"type": "string"},
        "map": {
            "type": "map",
            "mapping": {
                "key": {"type": "string"},
                "mode": {"type": "string"},
                "mode:xsoar": {"type": "string"},
                "mode:xsoar_saas": {"type": "string"},
                "mode:xsoar_on_prem": {"type": "string"},
                "mode:marketplacev2": {"type": "string"},
                "mode:xpanse": {"type": "string"},
            },
        },
        "is_fetch:xsoar": {"type": "string"},
        "is_fetch:marketplacev2": {"type": "string"},
        "is_fetch:xsoar_saas": {"type": "string"},
        "is_fetch:xsoar_on_prem": {"type": "string"},
        "is_fetch:xpanse": {"type": "string"},
    }
