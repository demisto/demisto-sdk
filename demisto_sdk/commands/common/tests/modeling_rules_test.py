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
