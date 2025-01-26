import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_pack_object,
)
from demisto_sdk.commands.validate.validators.VC_validators.VC100_valid_version_config_schema import (
    ValidVersionConfigSchema,
)
from demisto_sdk.commands.validate.validators.VC_validators.VC101_valid_version_config_versions import (
    ValidVersionConfigVersions,
)


@pytest.mark.parametrize(
    "expected_number_of_failures, content_items",
    [
        (
            0,
            [
                create_pack_object(
                    version_config={
                        "8.9": {"to": "1.5.0"},
                        "8.10": {"from": "1.5.1", "to": "2.0.0"},
                        "9.0": {"from": "2.0.1"},
                    }
                )
            ],
        ),
        (
            1,
            [
                create_pack_object(
                    version_config={
                        "not_platform_version": {"to": "1.5.0"},
                        "8.10": {"from": "1.5.1"},
                    }
                )
            ],
        ),
        (
            1,
            [
                create_pack_object(
                    version_config={"8.9": {"ot": "1.5.0"}, "8.10": {"from": "1.5.1"}}
                )
            ],
        ),
        (
            1,
            [
                create_pack_object(
                    version_config={"8.9": {"to": "1.5.0"}, "8.10": {"fom": "1.5.1"}}
                )
            ],
        ),
        (
            1,
            [
                create_pack_object(
                    version_config={
                        "8.9": {"to": "1.5.0"},
                        "8.10": {"from": "not_a_content_version"},
                    }
                )
            ],
        ),
    ],
    ids=[
        "valid_config_version",
        "invalid_platform_version",
        "invalid_to_field",
        "invalid_from_field",
        "invalid_content_version",
    ],
)
def test_isValidVersionConfigSchemaValid(expected_number_of_failures, content_items):
    """
    Given:
        case 1: valid_config_version = All fields are valid. from to and valid version.
        case 2: invalid_platform_version = Platform version has invalid version.
        case 3: invalid_to_field = to field is invalid.
        case 4: invalid_from_field = from field is invalid.
        case 5: invalid_content_version = Content version is invalid.
    When:
        - calling ValidVersionConfigSchema.obtain_invalid_content_items.

    Then:
        - case 1: Passes.
        - case 2: Fails. Invalid Platform version does not adhere to schema.
        - case 3: Fails. Invalid to field does not adhere to schema.
        - case 4: Fails. Invalid from field does not adhere to schema.
        - case 5: Fails. Invalid content version does not adhere to schema.
    """
    invalid_content_items = ValidVersionConfigSchema().obtain_invalid_content_items(
        content_items
    )
    assert len(invalid_content_items) == expected_number_of_failures
    if invalid_content_items:
        assert (
            invalid_content_items[0].message
            == "version config does not adhere to schema, does not use valid keys and values."
        )


@pytest.mark.parametrize(
    "expected_number_of_failures, content_items",
    [
        (
            0,
            [
                create_pack_object(
                    version_config={
                        "8.9": {"to": "1.5.0"},
                        "8.10": {"from": "1.5.1", "to": "2.0.0"},
                        "9.0": {"from": "2.0.1"},
                    }
                )
            ],
        ),
        (
            1,
            [
                create_pack_object(
                    version_config={"8.9": {"to": "1.5.0"}, "8.10": {"from": "1.5.2"}}
                )
            ],
        ),
        (
            1,
            [
                create_pack_object(
                    version_config={"8.9": {"to": "1.5.0"}, "8.10": {"to": "1.5.1"}}
                )
            ],
        ),
        (
            1,
            [
                create_pack_object(
                    version_config={
                        "8.9": {"to": "1.5.0"},
                        "8.10": {"from": "2.0.0", "to": "1.9.0"},
                    }
                )
            ],
        ),
        (
            1,
            [
                create_pack_object(
                    version_config={"8.12": {"to": "1.5.0"}, "8.10": {"from": "1.5.1"}}
                )
            ],
        ),
    ],
    ids=[
        "valid_config_version",
        "none_continuous_content_version",
        "closing_to_version",
        "bigger_from_than_to",
        "none_continuous_pack_version",
    ],
)
def test_isValidVersionConfigVersions(expected_number_of_failures, content_items):
    """
    Given:
        case 1: valid_config_version = Valid case consecutive versions.
        case 2: none_continuous_content_version = Content versions jumps from 1.5.0 to 1.5.2
        case 3: closing_to_version = Content version ends with a to. (can end with a from)
        case 4: bigger_from_than_to = Content version has a higher from version than to version.
        case 5: none_continuous_pack_version = Platform version is not consecutive.
    When:
        - calling ValidVersionConfigVersions.obtain_invalid_content_items.
    Then:
        - case 1: Passes.
        - case 2: Fails. Content version need to be consecutive.
        - case 3: Fails. Content version cant end with to.
        - case 4: Fails. From version should be lower than to.
        - case 5: Fails. Platform versions should be consecutive.
    """
    invalid_content_items = ValidVersionConfigVersions().obtain_invalid_content_items(
        content_items
    )
    assert len(invalid_content_items) == expected_number_of_failures
    if invalid_content_items:
        assert (
            invalid_content_items[0].message
            == "version config file does not adhere to platform content versions."
        )
