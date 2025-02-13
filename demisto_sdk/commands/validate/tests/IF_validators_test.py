from typing import List, Optional, Union

import pytest

from demisto_sdk.commands.common.constants import GitStatuses, MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_incident_field_object,
    create_incident_type_object,
    create_old_file_pointers,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF100_is_valid_name_and_cli_name import (
    IsValidNameAndCliNameValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF101_is_valid_content_field import (
    IsValidContentFieldValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF102_is_valid_system_flag import (
    IsValidSystemFlagValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF103_is_valid_field_type import (
    FIELD_TYPES,
    IsValidFieldTypeValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF104_is_valid_group_field import (
    REQUIRED_GROUP_VALUE,
    IsValidGroupFieldValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF105_is_cli_name_field_alphanumeric import (
    IsCliNameFieldAlphanumericValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF106_is_cli_name_reserved_word import (
    INCIDENT_PROHIBITED_CLI_NAMES,
    IsCliNameReservedWordValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF109_invalid_required_field import (
    IsValidRequiredFieldValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF111_is_field_type_changed import (
    IsFieldTypeChangedValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF113_name_field_prefix import (
    PACKS_IGNORE,
    NameFieldPrefixValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF115_unsearchable_key import (
    UnsearchableKeyValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF116_select_values_cannot_contain_empty_values_in_multi_select_types import (
    SelectValuesCannotContainEmptyValuesInMultiSelectTypesValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF117_invalid_marketplaces_in_alias import (
    IsValidAliasMarketplaceValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF118_is_alias_inner_alias_valid import (
    IsAliasInnerAliasValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF119_select_values_cannot_contain_multiple_or_only_empty_values_in_single_select_types import (
    SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator,
)
from TestSuite.test_tools import ChangeCWD


@pytest.mark.parametrize(
    "content_items, expected_msg",
    [
        pytest.param(
            create_incident_field_object(["name", "cliName"], ["case 1", "case1"]),
            "The following words cannot be used as a name: case.",
            id="One IncidentField with bad word in field `name`",
        ),
        pytest.param(
            create_incident_field_object(
                ["name", "cliName"], ["case incident 1", "caseincident1"]
            ),
            "The following words cannot be used as a name: case, incident.",
            id="IncidentField with two bad words in field `name`",
        ),
    ],
)
def test_IsValidNameAndCliNameValidator_not_valid(
    content_items: IncidentField,
    expected_msg: str,
):
    """
    Given:
        - IncidentFields content items
    When:
        - run obtain_invalid_content_items method
    Then:
        Case 1:
            - Ensure the error message is as expected
        Case 2:
            - Ensure the error message is as expected with the bad words list
    """
    results = IsValidNameAndCliNameValidator().obtain_invalid_content_items(
        content_items=[content_items]
    )
    assert results
    assert results[0].message == expected_msg


def test_IsValidContentFieldValidator_not_valid():
    """
    Given:
        - IncidentField content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that a ValidationResult (failure) is returned
          for the IncidentField whose 'content' field is set to False
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["content"], [False])
    ]

    results = IsValidContentFieldValidator().obtain_invalid_content_items(content_items)
    assert results
    assert results[0].message == "The `content` key must be set to true."


def test_IsValidSystemFlagValidator_not_valid():
    """
    Given:
        - IncidentField content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that a ValidationResult (failure) is returned
          for the IncidentField whose 'system' field is set to True
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["system"], [True])
    ]

    results = IsValidSystemFlagValidator().obtain_invalid_content_items(content_items)
    assert results
    assert results[0].message == "The `system` key must be set to false."


def test_IsValidFieldTypeValidator_not_valid():
    """
    Given:
        - IncidentField content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that a ValidationResult (failure) is returned
          for the IncidentField whose 'type' field is not valid
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["type"], ["test"])
    ]

    results = IsValidFieldTypeValidator().obtain_invalid_content_items(content_items)
    assert results
    assert (
        results[0].message
        == f"Type: `test` is not one of available types.\navailable types: {FIELD_TYPES}."
    )


def test_IsValidGroupFieldValidator_not_valid():
    """
    Given:
        - IncidentField content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that a ValidationResult (failure) is returned
          for the IncidentField whose 'group' field is not valid
    """
    content_items: List[IncidentField] = [create_incident_field_object(["group"], [2])]

    results = IsValidGroupFieldValidator().obtain_invalid_content_items(content_items)
    assert results
    assert results[0].message == "The `group` key must be set to 0 for Incident Field"


@pytest.mark.parametrize("cli_name_value", ["", "Foo", "123_", "123A"])
def test_IsCliNameFieldAlphanumericValidator_not_valid(cli_name_value):
    """
    Given:
        - IncidentField content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that a ValidationResult (failure) is returned
          for the IncidentField whose 'cliName' value is non-alphanumeric, or contains an uppercase letter.
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["cliName"], [cli_name_value])
    ]

    results = IsCliNameFieldAlphanumericValidator().obtain_invalid_content_items(
        content_items
    )
    assert results
    assert (
        results[0].message
        == "Field `cliName` contains uppercase or non-alphanumeric symbols."
    )


@pytest.mark.parametrize("reserved_word", INCIDENT_PROHIBITED_CLI_NAMES)
def test_IsCliNameReservedWordValidator_not_valid(reserved_word):
    """
    Given:
        - IncidentField content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that a ValidationResult (failure) is returned
          for the IncidentField whose 'cliName' value is a reserved word
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["cliName"], [reserved_word])
    ]

    results = IsCliNameReservedWordValidator().obtain_invalid_content_items(
        content_items
    )
    assert results
    assert (
        results[0].message
        == f"`cliName` field can not be `{reserved_word}` as it's a builtin key."
    )


def test_IsFieldTypeChangedValidator_obtain_invalid_content_items():
    """
    Given:
        - IncidentFiled content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that a ValidationResult (failure) is returned
          for the IncidentField whose 'type' field has changed
        - Ensure that no ValidationResult returned when 'type' field has not changed
    """
    old_type = "short text"
    new_type = "html"

    # not valid
    content_item = create_incident_field_object(["type"], [new_type])
    old_content_items = [create_incident_field_object(["type"], [old_type])]
    create_old_file_pointers([content_item], old_content_items)
    assert IsFieldTypeChangedValidator().obtain_invalid_content_items([content_item])

    # valid
    content_item.field_type = old_type
    assert not IsFieldTypeChangedValidator().obtain_invalid_content_items(
        [content_item]
    )


@pytest.mark.parametrize("unsearchable", (False, None))
def test_UnsearchableKeyValidator_obtain_invalid_content_items(
    unsearchable: Optional[bool],
):
    """
    Given:
        - IncidentFiled content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that a ValidationResult (failure) is returned
          for the IncidentField whose 'unsearchable' field is set to false or not or undefined
        - Ensure that no ValidationResult returned when unsearchable set to true
    """
    # not valid
    content_item = create_incident_field_object(
        paths=["unsearchable"], values=[unsearchable]
    )
    assert UnsearchableKeyValidator().obtain_invalid_content_items([content_item])

    # valid
    content_item.unsearchable = True
    assert not UnsearchableKeyValidator().obtain_invalid_content_items([content_item])


def test_NameFieldPrefixValidator_obtain_invalid_content_items_without_item_prefix():
    """
    Given:
        - IncidentField content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that a ValidationResult (failure) is returned
          for the IncidentField whose prefix name that not start with relevant pack name
    """
    # not valid
    pack_name = "Foo"
    with ChangeCWD(REPO.path):
        # Create an Incident field so that there is no prefix name of the pack in the name field
        content_item = create_incident_field_object(pack_info={"name": pack_name})
        assert not content_item.name.startswith(pack_name)
        results = NameFieldPrefixValidator().obtain_invalid_content_items(
            [content_item]
        )
        assert results
        assert results[0].message == (
            "Field name must start with the relevant pack name or one of the item prefixes found in pack metadata."
            "\nFollowing prefixes are allowed for this IncidentField:"
            f"\n{pack_name}"
        )

        # valid
        content_item.name = "Foo CVE"
        assert not NameFieldPrefixValidator().obtain_invalid_content_items(
            [content_item]
        )


@pytest.mark.parametrize(
    "item_prefix, valid_prefix, expected_allowed_prefixes",
    [
        pytest.param(
            ["Foo test", "Test Incident"],
            "Foo test CVE",
            ["Foo", "Foo test", "Test Incident"],
            id="itemPrefix is a list",
        ),
        pytest.param(
            "Foo test", "Foo test CVE", ["Foo", "Foo test"], id="itemPrefix is a str"
        ),
        pytest.param(None, "Foo CVE", ["Foo"], id="itemPrefix is None"),
    ],
)
def test_NameFieldPrefixValidator_obtain_invalid_content_items_with_item_prefix(
    item_prefix: Optional[Union[List[str], str]],
    valid_prefix: str,
    expected_allowed_prefixes: List[str],
):
    """
    Given:
        - IncidentField content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that a ValidationResult (failure) is returned
          for the IncidentField whose prefix name is not in `itemPrefix`
          which is in pack_metadata
        - Ensure that no ValidationResult returned when prefix name
          is in itemPrefix which is in pack_metadata
    """
    # not valid
    with ChangeCWD(REPO.path):
        content_item = create_incident_field_object(
            pack_info={"name": "Foo", "itemPrefix": item_prefix}
        )
        results = NameFieldPrefixValidator().obtain_invalid_content_items(
            [content_item]
        )
        assert results
        assert all(prefix in results[0].message for prefix in expected_allowed_prefixes)

        # valid
        content_item.name = valid_prefix
        assert not NameFieldPrefixValidator().obtain_invalid_content_items(
            [content_item]
        )


@pytest.mark.parametrize("special_pack", PACKS_IGNORE)
def test_NameFieldPrefixValidator_obtain_invalid_content_items_with_special_packs(
    special_pack: str,
):
    """
    Given:
        - IncidentField content item whose pack name is one of the special packs
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that no ValidationResult returned
    """
    with ChangeCWD(REPO.path):
        content_item = create_incident_field_object(pack_info={"name": special_pack})
        assert not NameFieldPrefixValidator().obtain_invalid_content_items(
            [content_item]
        )


def test_IsValidContentFieldValidator_valid():
    """
    Given:
        - IncidentField content items with a content value True
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["content"], [True])
    ]

    results = IsValidContentFieldValidator().obtain_invalid_content_items(content_items)
    assert not results


def test_IsValidSystemFlagValidator_valid():
    """
    Given:
        - IncidentField content items with a system value False
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["system"], [False])
    ]

    results = IsValidSystemFlagValidator().obtain_invalid_content_items(content_items)
    assert not results


def test_IsValidFieldTypeValidator_valid():
    """
    Given:
        - IncidentField content items with a valid type value
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["type"], ["html"])
    ]

    results = IsValidFieldTypeValidator().obtain_invalid_content_items(content_items)
    assert not results


def test_IsValidGroupFieldValidator_valid():
    """
    Given:
        - IncidentField content items with a group value 0
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items: List[IncidentField] = [create_incident_field_object(["group"], [0])]

    results = IsValidGroupFieldValidator().obtain_invalid_content_items(content_items)
    assert not results


@pytest.mark.parametrize("cli_name_value", ["foo1234", "foo", "1234"])
def test_IsCliNameFieldAlphanumericValidator_valid(cli_name_value):
    """
    Given:
        - IncidentField content items with a cliName value
          that is alphanumeric and lowercase letters
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["cliName"], [cli_name_value])
    ]

    results = IsCliNameFieldAlphanumericValidator().obtain_invalid_content_items(
        content_items
    )
    assert not results


def test_IsCliNameReservedWordValidator_valid():
    """
    Given:
        - IncidentField content items with a cliName value that is not reserve word
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["cliName"], ["foo"])
    ]

    results = IsCliNameReservedWordValidator().obtain_invalid_content_items(
        content_items
    )
    assert not results


def test_IsValidContentFieldValidator_fix():
    """
    Given:
        - invalid IncidentField that its 'content' field is set to False
    When:
        - run fix method
    Then:
        - Ensure the fix message as expected
        - Ensure the field `content` is set to true
    """
    incident_field = create_incident_field_object(["content"], [False])
    result = IsValidContentFieldValidator().fix(incident_field)
    assert result.message == "`content` field is set to true."
    assert incident_field.content


def test_IsValidSystemFlagValidator_fix():
    """
    Given:
        - invalid IncidentField that its 'system' field is set to True
    When:
        - run fix method
    Then:
        - Ensure the fix message as expected
        - Ensure the field `system` is set to false
    """
    incident_field = create_incident_field_object(["system"], [True])
    result = IsValidSystemFlagValidator().fix(incident_field)
    assert result.message == "`system` field is set to false."
    assert not incident_field.system


def test_IsValidGroupFieldValidator_fix():
    """
    Given:
        - invalid IncidentField that 'group' field is not 0
    When:
        - run fix method
    Then:
        - Ensure the fix message as expected
        - Ensure the field `group` is set to 0
    """
    incident_field = create_incident_field_object(["group"], [1])
    result = IsValidGroupFieldValidator().fix(incident_field)
    assert result.message == f"`group` field is set to {REQUIRED_GROUP_VALUE}."
    assert incident_field.group == REQUIRED_GROUP_VALUE


def test_IsFieldTypeChangedValidator_fix():
    """
    Given:
        - IncidentField that its `type` field has changed
    When:
        - run fix method
    Then:
        - Ensure the field `type` has changed back
    """
    old_type = "short text"
    new_type = "html"
    content_item = create_incident_field_object(["type"], [new_type])
    old_content_items = [create_incident_field_object(["type"], [old_type])]
    create_old_file_pointers([content_item], old_content_items)
    results = IsFieldTypeChangedValidator().fix(content_item)
    assert content_item.field_type == old_type
    assert results.message == f"Changed the `type` field back to `{old_type}`."


def test_SelectValuesCannotContainEmptyValuesInMultiSelectTypesValidator_valid():
    """
    Given:
        - valid IncidentField of type multySelect with no empty strings in selectValues key.
    When:
        - run obtain_invalid_content_items method.
    Then:
        - Ensure that ValidationResult returned as expected.
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(
            ["type", "selectValues"], ["multiSelect", ["blabla", "test"]]
        )
    ]
    results = SelectValuesCannotContainEmptyValuesInMultiSelectTypesValidator().obtain_invalid_content_items(
        content_items
    )
    assert not results


def test_SelectValuesCannotContainEmptyValuesInMultiSelectTypesValidator_invalid():
    """
    Given:
        - invalid IncidentField of type multySelect with empty strings in selectValues key.
    When:
        - run obtain_invalid_content_items method.
    Then:
        - Ensure that ValidationResult returned as expected.
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(
            ["type", "selectValues"], ["multiSelect", ["", "test"]]
        )
    ]
    results = SelectValuesCannotContainEmptyValuesInMultiSelectTypesValidator().obtain_invalid_content_items(
        content_items
    )
    assert results
    assert (
        results[0].message
        == "multiSelect types cannot contain empty values in the selectValues field."
    )


def test_SelectValuesCannotContainEmptyValuesInMultiSelectTypesValidator_fix():
    """
    Given:
        - invalid IncidentField of type multySelect with empty strings in selectValues key.
    When:
        - run fix method.
    Then:
        - Ensure the fix message is as expected.
        - Ensure there is no emtpy values in the selectValues field.
    """
    incident_field = create_incident_field_object(
        ["type", "selectValues"], ["singleSelect", ["", "", "test"]]
    )
    result = SelectValuesCannotContainEmptyValuesInMultiSelectTypesValidator().fix(
        incident_field
    )
    assert result.message == "Removed all empty values in the selectValues field."
    assert result.content_object.select_values == ["test"]


def test_SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator_multiple_empty_values_invalid():
    """
    Given:
        - invalid IncidentField of type singleSelect with multiple emtpy values in the selectValues filed.
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that ValidationResult runs as expected
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(
            ["type", "selectValues"], ["singleSelect", ["", "", "test"]]
        )
    ]
    results = SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator().obtain_invalid_content_items(
        content_items
    )
    assert results
    assert (
        results[0].message
        == "singleSelect types cannot contain more than one empty values in the selectValues field."
    )


def test_SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator_only_empty_values_invalid():
    """
    Given:
        - invalid IncidentField of type singleSelect with only one emtpy value in the selectValues filed.
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that ValidationResult runs as expected
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["type", "selectValues"], ["singleSelect", [""]])
    ]
    results = SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator().obtain_invalid_content_items(
        content_items
    )
    assert results
    assert (
        results[0].message
        == "singleSelect types cannot contain only empty values in the selectValues field."
    )


def test_SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator_only_one_empty_value_valid():
    """
    Given:
        - invalid IncidentField of type singleSelect with one emtpy value in the selectValues filed.
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that ValidationResult runs as expected
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(
            ["type", "selectValues"], ["singleSelect", ["", "test"]]
        )
    ]
    results = SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator().obtain_invalid_content_items(
        content_items
    )
    assert not results


def test_SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator_fix_only_empty_value():
    """
    Given:
        - invalid IncidentField of type singleSelect with only emtpy value in the selectValues filed.
    When:
        - run fix method.
    Then:
        - Ensure the fix returns an exception.
    """
    incident_field = create_incident_field_object(
        ["type", "selectValues"], ["singleSelect", [""]]
    )
    with pytest.raises(Exception) as exc_info:
        SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator().fix(
            incident_field
        )
        assert exc_info


def test_SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator_fix_multiple_empty_values():
    """
    Given:
        - invalid IncidentField of type singleSelect with multiple emtpy values in the selectValues filed.
    When:
        - run fix method.
    Then:
        - Ensure the fix message as expected
        - Ensure there is only one emtpy value in the selectValues field.
    """
    incident_field = create_incident_field_object(
        ["type", "selectValues"], ["singleSelect", ["", "", "test"]]
    )
    result = SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator().fix(
        incident_field
    )
    assert (
        result.message
        == "Removed all redundant empty values in the selectValues field."
    )
    assert result.content_object.select_values == ["test", ""]


def test_IsAliasInnerAliasValidator():
    """
    Given:
    - An incident field has an alias with an inner alias.
    When:
    - Running validate on an incident field.
    Then:
    - Validate that the correct aliases are caught.
    """
    inc_field = create_incident_field_object(
        ["Aliases"],
        [
            [
                {"cliName": "alias_1", "aliases": []},
                {"cliname": "alias_2", "aliases": []},
                {"cliName": "alias_3"},
            ]
        ],
    )

    result = IsAliasInnerAliasValidator().obtain_invalid_content_items([inc_field])

    assert (
        result[0].message
        == "The following aliases have inner aliases: alias_1, alias_2"
    )


def test_IsValidAliasMarketplaceValidator(mocker):
    """
    Given:
    - An incident field with aliases, one of them with invalid marketplaces field.
    When:
    - Running validate on an incident field.
    Then:
    - Validate that the incorrect alias is caught.
    """
    aliases_names = [
        {
            "cliName": "alias_1",
            "type": "shortText",
            "marketplaces": [MarketplaceVersions.XSOAR],
        },
        {
            "cliName": "alias_2",
            "type": "shortText",
            "marketplaces": [MarketplaceVersions.MarketplaceV2],
        },
    ]
    inc_field = create_incident_field_object(
        ["Aliases"],
        [aliases_names],
    )
    aliases = []
    for item in aliases_names:
        alias = create_incident_field_object(
            paths=["cliName"], values=[item.get("cliName")]
        )
        alias.marketplaces = item.get("marketplaces")
        aliases.append(alias)

    mocker.patch.object(IsValidAliasMarketplaceValidator, "graph", return_value="graph")
    mocker.patch.object(
        IsValidAliasMarketplaceValidator,
        "_get_incident_fields_by_aliases",
        return_value=aliases,
    )
    result = IsValidAliasMarketplaceValidator().obtain_invalid_content_items(
        [inc_field]
    )

    assert (
        result[0].message
        == "The following fields exist as aliases and have invalid 'marketplaces' key value: \nalias_2\n "
        "the value of the 'marketplaces' key in these fields should be ['xsoar']."
    )


@pytest.mark.parametrize(
    "items, expected_number_of_failures, expected_msgs",
    [
        (
            {
                create_incident_field_object(
                    paths=["required", "associatedToAll"], values=["false", "true"]
                ): GitStatuses.MODIFIED
            },
            0,
            [],
        ),  # inc field not required -> okay
        (
            {
                create_incident_field_object(
                    paths=["required", "associatedToAll"], values=["true", "true"]
                ): GitStatuses.ADDED
            },
            1,
            ["A required IncidentField should not be associated with all types."],
        ),
        (
            {
                create_incident_field_object(
                    paths=["required", "associatedToAll", "associatedTypes"],
                    values=["true", "false", ["New Type", "Old Type"]],
                ): GitStatuses.ADDED,
                create_incident_type_object(
                    paths=["id"], values=["New Type"]
                ): GitStatuses.ADDED,
            },
            1,
            [
                "An already existing Types like Old Type cannot be added to an IncidentField with required value equals true."
            ],
        ),
    ],
)
def test_IsValidRequiredFieldValidator(
    items, expected_number_of_failures, expected_msgs
):
    """
    Given:
    - Incident field not required.
    - Incident field which is required and associated to all
    - Incident field that is required, and an already existing incident type was added to it
    When:
    - Running validate on an incident fields.
    Then:
    - Validate that the field is valid.
    - Validate that the field is not valid, since required fields cannot be associated to all types
    - Validate that the field is not valid, since an already existing type cannot be added to a required field.
    """
    content_items = []
    for item, status in items.items():
        item.git_status = status
        item.old_base_content_object = item.copy(deep=True)
        content_items.append(item)

    result = IsValidRequiredFieldValidator().obtain_invalid_content_items(content_items)
    assert len(result) == len(expected_msgs)
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(result, expected_msgs)
        ]
    )
