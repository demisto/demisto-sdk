import os

from demisto_sdk.commands.common.hook_validations.modeling_rule import \
    ModelingRuleValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from TestSuite.test_tools import ChangeCWD


def test_is_valid_modeling_rule(repo):
    pack = repo.create_pack('TestPack')
    dummy_modeling_rule = pack.create_modeling_rule('MyRule')
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    with ChangeCWD(repo.path):
        modeling_rule_validator = ModelingRuleValidator(structure_validator)
        assert modeling_rule_validator.is_schema_file_exists()


def test_is_invalid_modeling_rule(repo):
    pack = repo.create_pack('TestPack')
    dummy_modeling_rule = pack.create_modeling_rule('MyRule')
    structure_validator = StructureValidator(dummy_modeling_rule.yml.path)
    schema_path = dummy_modeling_rule.schema.path
    if os.path.exists(schema_path):
        os.remove(schema_path)

    with ChangeCWD(repo.path):
        modeling_rule_validator = ModelingRuleValidator(structure_validator)
        assert not modeling_rule_validator.is_schema_file_exists()
