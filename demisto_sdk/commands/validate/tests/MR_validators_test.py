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
from demisto_sdk.commands.validate.validators.MR_validators.MR106_modeling_rule_scheme_types import (
    ModelingRuleSchemaTypesValidator,
)
from demisto_sdk.commands.validate.validators.MR_validators.MR107_is_schema_match_xif import (
    IsSchemaMatchXIFValidator,
)
from demisto_sdk.commands.validate.validators.MR_validators.MR108_invalid_modeling_rule_suffix_name import (
    ModelingRuleSuffixNameValidator,
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
        values=[
            "Example_" + MODELING_RULE_ID_SUFFIX,
            "Example " + MODELING_RULE_NAME_SUFFIX,
        ],
    )
    assert (
        len(
            ModelingRuleSuffixNameValidator().obtain_invalid_content_items(
                [modeling_rule]
            )
        )
        == 0
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
        paths=["id", "name"],
        values=["Example_", "Example " + MODELING_RULE_NAME_SUFFIX],
    )
    assert (
        len(
            ModelingRuleSuffixNameValidator().obtain_invalid_content_items(
                [modeling_rule]
            )
        )
        == 1
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
        paths=["id", "name"], values=["Example_" + MODELING_RULE_ID_SUFFIX, "Example "]
    )
    assert (
        len(
            ModelingRuleSuffixNameValidator().obtain_invalid_content_items(
                [modeling_rule]
            )
        )
        == 1
    )


def test_ValidateSchemaFileExistsValidator_obtain_invalid_content_items():
    """
    Given:
        - Modeling Rules content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that no ValidationResult returned when schema file exists.
        - Ensure that the ValidationResult returned when there is no schema file.
    """
    modeling_rule = create_modeling_rule_object()
    # Valid
    assert not ValidateSchemaFileExistsValidator().obtain_invalid_content_items(
        [modeling_rule]
    )

    # Schema file does not exist
    modeling_rule.schema_file.exist = False
    results = ValidateSchemaFileExistsValidator().obtain_invalid_content_items(
        [modeling_rule]
    )
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
        - run ModelingRuleSchemaTypesValidator().obtain_invalid_content_items method
    Then:

        - Ensure that no ValidationResult is returned when schema types exist.
        - Ensure that the ValidationResult is returned.
    """
    modeling_rule = create_modeling_rule_object()
    # Valid
    assert not ModelingRuleSchemaTypesValidator().obtain_invalid_content_items(
        [modeling_rule]
    )
    modeling_rule.schema_file.file_content = {
        "test": {"test_attribute": {"type": "Dict", "is_array": "false"}}
    }
    results = ModelingRuleSchemaTypesValidator().obtain_invalid_content_items(
        [modeling_rule]
    )
    # invalid
    assert (
        'The following types in the schema file are invalid: "Dict".'
        in results[0].message
    )


def test_IsSchemaMatchXIFValidator_obtain_invalid_content_items():
    """
    Given:
    - A list of modeling rules items
        Case 1: A valid modeling rule
        Case 2: Four invalid modeling rules objects
            - A modeling rule object without data sets in thx XIF file.
            - A modeling rule object without a schema file content.
            - A modeling rule object where len(xif_datasets) != len(schema_datasets).
            - A modeling rule object where len(xif_datasets) == len(schema_datasets) but schema_datasets != xif_datasets.
    When:
    - calling IsPlaybookContainUnhandledScriptConditionBranchesValidator.obtain_invalid_content_items.
    Then:
    - The results should be as expected:
        Case 1: The modeling rule object is valid.
        Case 2: All modeling rule objects failed.
    """
    validator = IsSchemaMatchXIFValidator()
    modeling_rule = create_modeling_rule_object(
        rules='[MODEL: dataset="test_audit_raw", model="Model", version=0.1]'
    )
    # Valid
    assert not validator.obtain_invalid_content_items([modeling_rule])

    # Case where there is a value in schema key
    modeling_rule_without_data_sets = create_modeling_rule_object(rules="test")
    modeling_rule_without_schema = create_modeling_rule_object()
    modeling_rule_without_schema.schema_file.file_content = {}
    modeling_rule_with_unequal_lengths = create_modeling_rule_object(
        schema={"test": 1, "test_2": 2}
    )
    modeling_rule_with_different_datasets = create_modeling_rule_object()
    invalid_modeling_rules = [
        modeling_rule_without_data_sets,
        modeling_rule_without_schema,
        modeling_rule_with_unequal_lengths,
        modeling_rule_with_different_datasets,
    ]
    results = validator.obtain_invalid_content_items(invalid_modeling_rules)
    assert len(results) == 4
    assert (
        results[0].message
        == "There is a mismatch between datasets in schema file and in the xif file. Either there are more datasets declared in one of the files, or the datasets titles are not the same."
    )
