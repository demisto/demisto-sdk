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
                "regex;(mode:(xsoar)|(marketplacev2)|(xpanse)|(xsoar_on_prem)|(xsoar_saas))": {
                    "type": "string"
                },
            },
        },
        "regex;(isfetch:(xsoar)|(marketplacev2)|(xpanse)|(xsoar_on_prem)|(xsoar_saas))": {
            "type": "string"
        },
    }
