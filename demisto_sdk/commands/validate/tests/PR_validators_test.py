from demisto_sdk.commands.validate.tests.test_tools import (
    create_parsing_rule_object,
    create_modeling_rule_object,
)
from demisto_sdk.commands.validate.validators.PR_validators.PR101_invalid_parsing_or_modeling_rule_suffix_name import (
    ParsingAndModelingRuleSuffixNameValidator,
)
from demisto_sdk.commands.common.constants import (
    MODELING_RULE,
    MODELING_RULE_ID_SUFFIX,
    MODELING_RULE_NAME_SUFFIX,
    PARSING_RULE,
    PARSING_RULE_ID_SUFFIX,
    PARSING_RULE_NAME_SUFFIX,
)

def test_parsing_rule_with_valid_suffixes():
    parsing_rule = create_parsing_rule_object (
        ["object_id", "name"], ["Example_ParsingRule", "Example Parsing Rule"]
    )
    assert len(ParsingAndModelingRuleSuffixNameValidator().is_valid([parsing_rule])) == 0
    
def test_modeling_rule_with_valid_suffixes():
    modeling_rule = create_modeling_rule_object (
        ["object_id", "name"], ["Example_ModelingRule", "Example Modeling Rule"]
    )
    assert len(ParsingAndModelingRuleSuffixNameValidator().is_valid([modeling_rule])) == 0


def test_parsing_rule_with_invalid_id_suffix():
    parsing_rule = create_parsing_rule_object (
        ["object_id", "name"], ["Example_", "Example Parsing Rule"]
    )
    assert len(ParsingAndModelingRuleSuffixNameValidator().is_valid([parsing_rule])) == 1

def test_parsing_rule_with_invalid_name_suffix():
    parsing_rule = create_parsing_rule_object (
        ["object_id", "name"], ["Example_ParsingRule", "Example Parsing"]
    )
    assert len(ParsingAndModelingRuleSuffixNameValidator().is_valid([parsing_rule])) == 0
    

def test_modeling_rule_with_invalid_id_suffix():
    
    
def test_modeling_rule_with_invalid_name_suffix():