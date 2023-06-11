import os

import pytest

from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.hook_validations.modeling_rule import (
    ModelingRuleValidator,
)
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from TestSuite.test_tools import ChangeCWD

yaml = YAML_Handler()


def test_is_valid_modeling_rule(repo):
    """
    Given: A valid modeling rule with a schema file
    When: running is_schema_file_exists
    Then: Validate that the modeling rule is valid

    """
    pack = repo.create_pack("TestPack")
    dummy_modeling_rule = pack.create_modeling_rule("MyRule")
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    with ChangeCWD(repo.path):
        modeling_rule_validator = ModelingRuleValidator(structure_validator)
        assert modeling_rule_validator.is_schema_file_exists()


def test_is_invalid_modeling_rule(repo):
    """
    Given: An invalid modeling rule without a schema file
    When: running is_schema_file_exists
    Then: Validate that the modeling rule is invalid
    """
    pack = repo.create_pack("TestPack")
    dummy_modeling_rule = pack.create_modeling_rule("MyRule")
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    schema_path = dummy_modeling_rule.schema.path
    if os.path.exists(schema_path):
        os.remove(schema_path)

    with ChangeCWD(repo.path):
        modeling_rule_validator = ModelingRuleValidator(structure_validator)
        assert not modeling_rule_validator.is_schema_file_exists()


def test_is_not_empty_rules_key(repo):
    """
    Given: A modeling rule yml with rules key not empty (invalid)
    When: running are_keys_empty_in_yml
    Then: Validate that the modeling rule is invalid
    """
    yml_dict = {
        "id": "modeling-rule",
        "name": "Modeling Rule",
        "fromversion": 3.3,
        "tags": "tag",
        "rules": "This is a test - not empty",
        "schema": "",
    }
    pack = repo.create_pack("TestPack")
    dummy_modeling_rule = pack.create_modeling_rule("MyRule")
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    dummy_modeling_rule.yml.write_dict(yml_dict)

    with ChangeCWD(repo.path):
        modeling_rule_validator = ModelingRuleValidator(structure_validator)
        assert not modeling_rule_validator.are_keys_empty_in_yml()


def test_is_not_empty_schema_key(repo):
    """
    Given: A modeling rule yml with schema key not empty (invalid)
    When: running are_keys_empty_in_yml
    Then: Validate that the modeling rule is invalid
    """
    yml_dict = {
        "id": "modeling-rule",
        "name": "Modeling Rule",
        "fromversion": 3.3,
        "tags": "tag",
        "rules": "",
        "schema": "This is a test - not empty",
    }
    pack = repo.create_pack("TestPack")
    dummy_modeling_rule = pack.create_modeling_rule("MyRule")
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    dummy_modeling_rule.yml.write_dict(yml_dict)

    with ChangeCWD(repo.path):
        modeling_rule_validator = ModelingRuleValidator(structure_validator)
        assert not modeling_rule_validator.are_keys_empty_in_yml()


def test_is_missing_key_from_yml(repo):
    """
    Given: A modeling rule yml with schema key missing
    When: running are_keys_empty_in_yml
    Then: Validate that the modeling rule is invalid
    """
    yml_dict = {
        "id": "modeling-rule",
        "name": "Modeling Rule",
        "fromversion": 3.3,
        "tags": "tag",
        "rules": "",
    }
    pack = repo.create_pack("TestPack")
    dummy_modeling_rule = pack.create_modeling_rule("MyRule")
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    dummy_modeling_rule.yml.write_dict(yml_dict)

    with ChangeCWD(repo.path):
        modeling_rule_validator = ModelingRuleValidator(structure_validator)
        assert not modeling_rule_validator.are_keys_empty_in_yml()


def test_is_valid_rule_file_name(repo):
    """
    Given: A modeling rule with valid component file names
    When: running is_valid_rule_names
    Then: Validate that the modeling rule is valid
    """
    pack = repo.create_pack("TestPack")
    dummy_modeling_rule = pack.create_modeling_rule("MyRule")
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    with ChangeCWD(repo.path):
        modeling_rule_validator = ModelingRuleValidator(structure_validator)
        assert modeling_rule_validator.is_valid_rule_names()


files_to_rename = ["xif", "yml", "schema", "testdata"]


@pytest.mark.parametrize("file_to_rename", files_to_rename)
def test_is_invalid_rule_file_name(repo, file_to_rename):
    """
    Given: A modeling rule with invalid component file name
    When: running is_valid_rule_names
    Then: Validate that the modeling rule is invalid
    """
    pack = repo.create_pack("TestPack")
    dummy_modeling_rule = pack.create_modeling_rule("MyRule")
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    if file_to_rename == "xif":
        path_to_replace = dummy_modeling_rule.rules.path
        new_name = f'{path_to_replace.rsplit("/", 1)[0]}/MyRule1.xif'
    elif file_to_rename == "yml":
        path_to_replace = dummy_modeling_rule.yml.path
        new_name = f'{path_to_replace.rsplit("/", 1)[0]}/MyRule1.yml'
    elif file_to_rename == "schema":
        path_to_replace = dummy_modeling_rule.schema.path
        new_name = f'{path_to_replace.rsplit("/", 1)[0]}/MyRule1_schema.json'
    else:
        path_to_replace = dummy_modeling_rule.testdata.path
        new_name = f'{path_to_replace.rsplit("/", 1)[0]}/MyRule1_testdata.json'
    os.rename(path_to_replace, new_name)

    with ChangeCWD(repo.path):
        modeling_rule_validator = ModelingRuleValidator(structure_validator)
        assert not modeling_rule_validator.is_valid_rule_names()
        assert not modeling_rule_validator._is_valid


@pytest.mark.parametrize(
    "schema, valid",
    [
        ({"test_audit_raw": {"name": {"type": "sting", "is_array": False}}}, False),
        ({"test_audit_raw": {"name": {"type": "string", "is_array": False}}}, True),
    ],
)
def test_is_schema_types_valid(repo, schema, valid):
    """
    Given: A modeling rule with invalid schema attribute types
    When: running is_schema_types_valid
    Then: Validate that the modeling rule is invalid
    """
    pack = repo.create_pack("TestPack")
    dummy_modeling_rule = pack.create_modeling_rule("MyRule", schema=schema)
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    modeling_rule_validator = ModelingRuleValidator(structure_validator)
    assert modeling_rule_validator.is_schema_types_valid() == valid


def mock_handle_error(error_message, error_code, file_path):
    return error_message


@pytest.mark.parametrize(
    "rule_file_name, rule_dict, expected_error, valid",
    [
        (
            "MyRule",
            {"id": "modeling-rule", "name": "Modeling-Rule"},
            "\nThe file name should end with 'ModelingRules.yml'\nThe rule id should end with 'ModelingRule'\nThe rule name should end with 'Modeling Rule'",
            False,
        ),
        (
            "MyRule",
            {"id": "ModelingRule", "name": "Modeling Rule"},
            "\nThe file name should end with 'ModelingRules.yml'",
            False,
        ),
        (
            "MyRuleModelingRules",
            {"id": "modeling-rule", "name": "Modeling Rule"},
            "\nThe rule id should end with 'ModelingRule'",
            False,
        ),
        (
            "MyRuleModelingRules",
            {"id": "ModelingRule", "name": "Modeling-Rule"},
            "\nThe rule name should end with 'Modeling Rule'",
            False,
        ),
        (
            "MyRuleModelingRules",
            {"id": "ModelingRule", "name": "Modeling Rule"},
            "",
            True,
        ),
        (
            "MyRuleModelingRules_1_3",
            {"id": "ModelingRule", "name": "Modeling Rule"},
            "",
            True,
        ),
        (
            "MyRuleModelingRules_1_!@#",
            {"id": "ModelingRule", "name": "Modeling Rule"},
            "\nThe file name should end with 'ModelingRules.yml'",
            False,
        ),
    ],
)
def test_is_suffix_name_valid(
    mocker, repo, rule_file_name, rule_dict, expected_error, valid
):
    """
    Given: A modeling rule with valid/invalid file_name/id/name
        case 1: Wrong file_name id and name.
        case 2: Wrong file_name.
        case 3: Wrong id.
        case 4: Wrong name.
        case 5: Correct file_name id and name.
        case 6: Correct file_name (with version) id and name.
        case 7: Wrong file_name (wrong version).
    When: running is_valid_rule_suffix_name.
    Then: Validate that the modeling rule is valid/invalid and the message (in case of invalid) is as expected.
    """
    pack = repo.create_pack("TestPack")
    dummy_modeling_rule = pack.create_modeling_rule(rule_file_name)
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    dummy_modeling_rule.yml.write_dict(rule_dict)
    error_message = mocker.patch(
        "demisto_sdk.commands.common.hook_validations.modeling_rule.ModelingRuleValidator.handle_error",
        side_effect=mock_handle_error,
    )

    with ChangeCWD(repo.path):
        modeling_rule_validator = ModelingRuleValidator(structure_validator)
        assert modeling_rule_validator.is_valid_rule_suffix_name() == valid
        if not valid:
            assert (
                error_message.call_args[0][0].split("please check the following:")[1]
                == expected_error
            )


def test_dataset_name_matches_in_xif_and_schema(repo):
    """
    Given: A modeling rule with mismatch between dataset name of the schema and xif files.
    When: running dataset_name_matches_in_xif_and_schema.
    Then: Validate that the modeling rule is invalid.
    """
    pack = repo.create_pack("TestPack")
    dummy_modeling_rule = pack.create_modeling_rule("MyRule")
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    modeling_rule_validator = ModelingRuleValidator(structure_validator)
    assert not modeling_rule_validator.dataset_name_matches_in_xif_and_schema()
