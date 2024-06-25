from demisto_sdk.commands.validate.tests.test_tools import (
    create_modeling_rule_object,
)
from demisto_sdk.commands.validate.validators.MR_validators.MR100_validate_schema_file_exists import (
    ValidateSchemaFileExistsValidator,
)
from demisto_sdk.commands.validate.validators.MR_validators.MR101_validate_empty_keys import (
    ValidateEmptyKeysValidator,
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
