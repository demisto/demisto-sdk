from demisto_sdk.commands.validate.tests.test_tools import (
    create_modeling_rule_object,
)
from demisto_sdk.commands.validate.validators.MR_validators.MR100_validate_schema_file_exists import (
    ValidateSchemaFileExistsValidator,
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
