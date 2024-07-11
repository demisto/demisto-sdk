from demisto_sdk.commands.common.constants import (
    MODELING_RULE_ID_SUFFIX,
    MODELING_RULE_NAME_SUFFIX,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    create_modeling_rule_object,
)
from demisto_sdk.commands.validate.validators.MR_validators.MR100_validate_schema_file_exists import (
    ValidateSchemaFileExistsValidator,
)
from demisto_sdk.commands.validate.validators.MR_validators.MR101_validate_empty_keys import (
    ValidateEmptyKeysValidator,
)
from demisto_sdk.commands.validate.validators.MR_validators.MR106_modeling_rule_scheme_types import (
    ModelingRuleSchemaTypesValidator,
)


def test_modeling_rule_with_valid_suffixes():
    """
    Given:
        A modeling rule with valid name and id.
    When:
        Calling Validate.
    Then:
        The validation should not fail.
    """
    modeling_rule = create_modeling_rule_object(
        paths=["id", "name"],
        values=["Example_" + MODELING_RULE_ID_SUFFIX, "Example " + MODELING_RULE_NAME_SUFFIX],
    )
    assert (
        len(ModelingRuleSchemaTypesValidator().is_valid([modeling_rule])) == 0
    )
    

def test_modeling_rule_with_invalid_id_suffix():
    """
    Given:
        A modeling rule with valid name but invalid id.
    When:
        Calling Validate.
    Then:
        The validation should fail.
    """
    modeling_rule = create_modeling_rule_object(
        paths=["id", "name"], values=["Example_", "Example " + MODELING_RULE_NAME_SUFFIX]
    )
    assert (
        len(ModelingRuleSchemaTypesValidator().is_valid([modeling_rule])) == 1
    )


def test_modeling_rule_with_invalid_name_suffix():
    """
    Given:
        A modeling rule with valid id but invalid name.
    When:
        Calling Validate.
    Then:
        The validation should fail.
    """
    modeling_rule = create_modeling_rule_object(
       paths= ["id", "name"], values=["Example_" + MODELING_RULE_ID_SUFFIX, "Example "]
    )
    assert (
        len(ModelingRuleSchemaTypesValidator().is_valid([modeling_rule])) == 1
    )


def test_ValidateSchemaFileExistsValidator_is_valid():
    """
    Given:
        - Modeling Rules content items
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned when schema file exists.
        - Ensure that the ValidationResult returned when there is no schema file.
    """
    modeling_rule = create_modeling_rule_object()
    # Valid
    assert not ValidateSchemaFileExistsValidator().is_valid([modeling_rule])

    # Schema file does not exist
    modeling_rule.schema_file.exist = False
    results = ValidateSchemaFileExistsValidator().is_valid([modeling_rule])
    assert (
        'The modeling rule "Duo Modeling Rule" is missing a schema file.'
        == results[0].message
    )


def test_ModelingRuleSchemaTypesValidator_valid():
    """
    Given:
    - Modeling Rules content items:
        - Modeling Rules content items with valid schema types
        - Modeling Rules content items with invalid schema types
    When:
        - run ModelingRuleSchemaTypesValidator().is_valid method
    Then:

        - Ensure that no ValidationResult is returned when schema types exist.
        - Ensure that the ValidationResult is returned.
    """
    modeling_rule = create_modeling_rule_object()
    # Valid
    assert not ModelingRuleSchemaTypesValidator().is_valid([modeling_rule])
    modeling_rule.schema_file.file_content = {
        "test": {"test_attribute": {"type": "Dict", "is_array": "false"}}
    }
    results = ModelingRuleSchemaTypesValidator().is_valid([modeling_rule])
    # invalid
    assert (
        'The following types in the schema file are invalid: "Dict".'
        in results[0].message
    )


def test_ValidateEmptyKeysValidator_is_valid():
    """
    Given:
        - Modeling Rules content items
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned when modeling rule has the right keys.
        - Ensure that the ValidationResult returned when:
            - One of the keys has a value in it (test instead of empty string).
            - One of the keys does not exist as all.
    """
    modeling_rule = create_modeling_rule_object()
    # Valid
    assert not ValidateEmptyKeysValidator().is_valid([modeling_rule])

    # Case where there is a value in schema key
    modeling_rule.schema_key = "test"
    results = ValidateEmptyKeysValidator().is_valid([modeling_rule])
    assert (
        "Either the 'rules' key or the 'schema' key are missing or not empty, "
        "make sure to set the values of these keys to an empty string."
        == results[0].message
    )

    # Case where the rules key does not exist.
    modeling_rule.rules_key = None
    results = ValidateEmptyKeysValidator().is_valid([modeling_rule])
    assert (
        "Either the 'rules' key or the 'schema' key are missing or not empty, "
        "make sure to set the values of these keys to an empty string."
        == results[0].message
    )
