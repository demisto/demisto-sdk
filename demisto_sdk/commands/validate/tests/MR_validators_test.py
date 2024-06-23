from demisto_sdk.commands.validate.tests.test_tools import (
    create_modeling_rule_object,
)
from demisto_sdk.commands.validate.validators.MR_validators.MR100_validate_schema_file_exists import (
    ValidateSchemaFileExistsValidator,
)

from demisto_sdk.commands.validate.validators.MR_validators.MR106_modeling_rule_scheme_types import (
    ModelingRuleSchemaTypesValidator
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
            - Modeling Rules content items with valid schema types
        When:
            - run ModelingRuleSchemaTypesValidator().is_valid method
        Then:
            - Ensure that no ValidationResult returned when schema types exists.
    """
    modeling_rule = create_modeling_rule_object(
        paths=["schema_file"],
        values=['{"test": {"test_attribute": {"type": "string","is_array": "false"}}']
    )
    # Valid
    assert not ModelingRuleSchemaTypesValidator().is_valid([modeling_rule])


def test_ModelingRuleSchemaTypesValidator_invalid():
    """
        Given:
            - Modeling Rules content items with invalid schema types
        When:
            - run ModelingRuleSchemaTypesValidator().is_valid method
        Then:
            - Ensure that the ValidationResult returned.
    """
    modeling_rule = create_modeling_rule_object(
        paths=["schema_file"],
        values=['{"test": {"test_attribute": {"type": "Dict","is_array": "false"}}']
    )
    # Valid
    results = ModelingRuleSchemaTypesValidator().is_valid([modeling_rule])
    assert (
            'The modeling rule "Duo Modeling Rule" is missing a schema file.'
            == results[0].message
    )
