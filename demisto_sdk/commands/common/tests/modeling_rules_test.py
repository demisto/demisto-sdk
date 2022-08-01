import os

from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.hook_validations.modeling_rule import \
    ModelingRuleValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from TestSuite.test_tools import ChangeCWD

yaml = YAML_Handler()


def test_is_valid_modeling_rule(repo):
    """
    Given: A valid modeling rule with a schema file
    When: running is_schema_file_exists
    Then: Validate that the modeling rule is valid

    """
    pack = repo.create_pack('TestPack')
    dummy_modeling_rule = pack.create_modeling_rule('MyRule')
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
    pack = repo.create_pack('TestPack')
    dummy_modeling_rule = pack.create_modeling_rule('MyRule')
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
        'id': 'modeling-rule',
        'name': 'Modeling Rule',
        'fromversion': 3.3,
        'tags': 'tag',
        'rules': 'This is a test - not empty',
        'schema': '',
    }
    pack = repo.create_pack('TestPack')
    dummy_modeling_rule = pack.create_modeling_rule('MyRule')
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
        'id': 'modeling-rule',
        'name': 'Modeling Rule',
        'fromversion': 3.3,
        'tags': 'tag',
        'rules': '',
        'schema': 'This is a test - not empty',
    }
    pack = repo.create_pack('TestPack')
    dummy_modeling_rule = pack.create_modeling_rule('MyRule')
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
        'id': 'modeling-rule',
        'name': 'Modeling Rule',
        'fromversion': 3.3,
        'tags': 'tag',
        'rules': '',
    }
    pack = repo.create_pack('TestPack')
    dummy_modeling_rule = pack.create_modeling_rule('MyRule')
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    dummy_modeling_rule.yml.write_dict(yml_dict)

    with ChangeCWD(repo.path):
        modeling_rule_validator = ModelingRuleValidator(structure_validator)
        assert not modeling_rule_validator.are_keys_empty_in_yml()


def test_is_invalid_rule_file_name(repo):
    """
    Given: A modeling rule with invalid schema name
    When: running is_valid_rule_names
    Then: Validate that the modeling rule is invalid
    """
    pack = repo.create_pack('TestPack')
    dummy_modeling_rule = pack.create_modeling_rule('MyRule')
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    schema_path = dummy_modeling_rule.schema.path
    new_name = f'{schema_path.rsplit("/", 1)[0]}/MyRule1.json'
    os.rename(schema_path, new_name)

    with ChangeCWD(repo.path):
        modeling_rule_validator = ModelingRuleValidator(structure_validator)
        assert not modeling_rule_validator.is_valid_rule_names()
