import pytest

from demisto_sdk.commands.common.constants import (
    MODELING_RULE_ID_SUFFIX,
    MODELING_RULE_NAME_SUFFIX,
    ExecutionMode,
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
from demisto_sdk.commands.validate.validators.MR_validators.MR109_user_field_missing_identity import (
    UserFieldMissingIdentityValidator,
)
from demisto_sdk.commands.validate.validators.MR_validators.MR110_modeling_rule_schema_descriptions import (
    ModelingRuleSchemaDescriptionsValidator,
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


def test_ModelingRuleSchemaTypesValidator_with_descriptions():
    """
    Given:
        - A modeling rule whose schema contains dataset_description and field_description fields.
    When:
        - run ModelingRuleSchemaTypesValidator().obtain_invalid_content_items method
    Then:
        - Ensure the descriptions are ignored and no ValidationResult is returned.
    """
    modeling_rule = create_modeling_rule_object()
    modeling_rule.schema_file.file_content = {
        "test": {
            "dataset_description": "Audit logs.",
            "test_attribute": {
                "type": "string",
                "is_array": False,
                "field_description": "A description.",
            },
        }
    }
    assert not ModelingRuleSchemaTypesValidator().obtain_invalid_content_items(
        [modeling_rule]
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


def test_UserFieldMissingIdentityValidator_valid():
    """
    Given: A modeling rule XIF where every user field has a matching identity field
        (including a sub-namespace field and backtick-quoted identifiers).
    When: Calling UserFieldMissingIdentityValidator.obtain_invalid_content_items.
    Then: The validation should not fail.
    """
    rules = (
        '[MODEL: dataset="user_identity_raw"]\n'
        "alter\n"
        "    xdm.source.user.username = a, xdm.source.identity.username = a,\n"
        "    xdm.source.user.group.guid = g, xdm.source.identity.group.guid = g,\n"
        "    xdm.target.`user`.name = b, xdm.target.`identity`.name = b;"
    )
    modeling_rule = create_modeling_rule_object(rules=rules)
    assert not UserFieldMissingIdentityValidator().obtain_invalid_content_items(
        [modeling_rule]
    )


def test_UserFieldMissingIdentityValidator_user_without_identity():
    """
    Given: A modeling rule XIF where a user field has no identity counterpart, the
        counterpart only appears in a comment, and xdm.*.user.* also appears as a
        right-hand-side argument (which must be ignored).
    When: Calling UserFieldMissingIdentityValidator.obtain_invalid_content_items.
    Then: The validation should fail and report the missing user field.
    """
    rules = (
        '[MODEL: dataset="user_identity_raw"]\n'
        "alter\n"
        "    xdm.source.user.username = to_string(xdm.source.user.username), "
        "// xdm.source.identity.username = x\n"
        "    xdm.source.user.policy.name = p;"
    )
    modeling_rule = create_modeling_rule_object(rules=rules)
    results = UserFieldMissingIdentityValidator().obtain_invalid_content_items(
        [modeling_rule]
    )
    assert len(results) == 1
    assert "xdm.source.user.username" in results[0].message
    assert "xdm.source.user.policy.name" in results[0].message


def test_UserFieldMissingIdentityValidator_identity_without_user_is_valid():
    """
    Given: A modeling rule XIF that maps only xdm.target.identity.username (no user).
    When: Calling UserFieldMissingIdentityValidator.obtain_invalid_content_items.
    Then: The validation should not fail (the check is only user -> identity).
    """
    rules = (
        '[MODEL: dataset="user_identity_raw"]\n'
        "alter\n"
        "    xdm.target.identity.username = t;"
    )
    modeling_rule = create_modeling_rule_object(rules=rules)
    assert not UserFieldMissingIdentityValidator().obtain_invalid_content_items(
        [modeling_rule]
    )


def test_UserFieldMissingIdentityValidator_skips_old_versioned_rule():
    """
    Given: An old (non-latest) modeling rule - its yml has an explicit toversion -
        that maps a user field with no identity counterpart.
    When: Calling UserFieldMissingIdentityValidator.obtain_invalid_content_items.
    Then: The validation should skip the old rule.
    """
    rules = (
        '[MODEL: dataset="user_identity_raw"]\nalter\n    xdm.source.user.username = a;'
    )
    modeling_rule = create_modeling_rule_object(
        paths=["toversion"], values=["8.8.0"], rules=rules
    )
    assert not UserFieldMissingIdentityValidator().obtain_invalid_content_items(
        [modeling_rule]
    )


def test_UserFieldMissingIdentityValidator_ignores_non_listed_prefix():
    """
    Given: A modeling rule XIF with a user field under a prefix that is not one of
        source/intermediate/target (e.g. xdm.observer.user.*), with no identity field.
    When: Calling UserFieldMissingIdentityValidator.obtain_invalid_content_items.
    Then: The validation should not fail, because only source/intermediate/target
        prefixes are checked.
    """
    rules = (
        '[MODEL: dataset="user_identity_raw"]\nalter\n    xdm.observer.user.name = x;'
    )
    modeling_rule = create_modeling_rule_object(rules=rules)
    assert not UserFieldMissingIdentityValidator().obtain_invalid_content_items(
        [modeling_rule]
    )


def test_UserFieldMissingIdentityValidator_unequal_counts_fail():
    """
    Given: A modeling rule XIF that assigns xdm.source.user.username twice but its
        matching xdm.source.identity.username only once (one identity mapping was
        removed from one of the blocks).
    When: Calling UserFieldMissingIdentityValidator.obtain_invalid_content_items.
    Then: The validation should fail, because the number of user assignments must
        equal the number of matching identity assignments.
    """
    rules = (
        '[MODEL: dataset="user_identity_raw"]\n'
        "alter\n"
        "    xdm.source.user.username = a, xdm.source.identity.username = a;\n"
        "alter\n"
        "    xdm.source.user.username = b;"
    )
    modeling_rule = create_modeling_rule_object(rules=rules)
    results = UserFieldMissingIdentityValidator().obtain_invalid_content_items(
        [modeling_rule]
    )
    assert len(results) == 1
    assert "xdm.source.user.username" in results[0].message


def test_UserFieldMissingIdentityValidator_equal_counts_valid():
    """
    Given: A modeling rule XIF that assigns xdm.source.user.username twice and its
        matching xdm.source.identity.username twice (in separate blocks).
    When: Calling UserFieldMissingIdentityValidator.obtain_invalid_content_items.
    Then: The validation should not fail, because the counts match.
    """
    rules = (
        '[MODEL: dataset="user_identity_raw"]\n'
        "alter\n"
        "    xdm.source.user.username = a, xdm.source.identity.username = a;\n"
        "alter\n"
        "    xdm.source.user.username = b, xdm.source.identity.username = b;"
    )
    modeling_rule = create_modeling_rule_object(rules=rules)
    assert not UserFieldMissingIdentityValidator().obtain_invalid_content_items(
        [modeling_rule]
    )


def test_ModelingRuleSchemaDescriptionsValidator_valid():
    """
    Given:
        - A modeling rule whose schema has a dataset_description for every dataset
          and a field_description for every field.
    When:
        - run ModelingRuleSchemaDescriptionsValidator().obtain_invalid_content_items method
    Then:
        - Ensure no ValidationResult is returned.
    """
    modeling_rule = create_modeling_rule_object()
    modeling_rule.schema_file.file_content = {
        "test_raw": {
            "dataset_description": "Audit logs.",
            "field1": {
                "type": "string",
                "is_array": False,
                "field_description": "First field.",
            },
            "field2": {
                "type": "int",
                "is_array": False,
                "field_description": "Second field.",
            },
        }
    }
    assert not ModelingRuleSchemaDescriptionsValidator().obtain_invalid_content_items(
        [modeling_rule]
    )


@pytest.mark.parametrize(
    "schema, expected_in_message, expected_not_in_message",
    [
        pytest.param(
            {
                "test_raw": {
                    "field1": {
                        "type": "string",
                        "is_array": False,
                        "field_description": "First field.",
                    },
                }
            },
            ["Datasets without dataset_description: test_raw."],
            ["Fields without field_description"],
            id="missing dataset_description",
        ),
        pytest.param(
            {
                "test_raw": {
                    "dataset_description": "Audit logs.",
                    "field1": {"type": "string", "is_array": False},
                    "field2": {
                        "type": "string",
                        "is_array": False,
                        "field_description": "Second field.",
                    },
                }
            },
            ["Fields without field_description: test_raw.field1."],
            ["Datasets without dataset_description", "test_raw.field2"],
            id="missing field_description",
        ),
        pytest.param(
            {
                "test_raw": {
                    "dataset_description": "",
                    "field1": {
                        "type": "string",
                        "is_array": False,
                        "field_description": "   ",
                    },
                }
            },
            [
                "Datasets without dataset_description: test_raw.",
                "Fields without field_description: test_raw.field1.",
            ],
            [],
            id="empty and whitespace-only descriptions",
        ),
        pytest.param(
            {
                "first_raw": {
                    "field1": {"type": "string", "is_array": False},
                },
                "second_raw": {
                    "dataset_description": "Second dataset.",
                    "field2": {"type": "string", "is_array": False},
                },
            },
            [
                "Datasets without dataset_description: first_raw.",
                "Fields without field_description: first_raw.field1, second_raw.field2.",
            ],
            [],
            id="multiple datasets, all affected items listed",
        ),
    ],
)
def test_ModelingRuleSchemaDescriptionsValidator_invalid(
    schema, expected_in_message, expected_not_in_message
):
    """
    Given:
        - A modeling rule whose schema is missing, or has empty, descriptions.
    When:
        - run ModelingRuleSchemaDescriptionsValidator().obtain_invalid_content_items method
    Then:
        - Ensure a single ValidationResult is returned, on the schema file,
          listing all the affected datasets and fields.
    """
    modeling_rule = create_modeling_rule_object()
    modeling_rule.schema_file.file_content = schema
    results = ModelingRuleSchemaDescriptionsValidator().obtain_invalid_content_items(
        [modeling_rule]
    )
    assert len(results) == 1
    assert results[0].path == modeling_rule.schema_file.file_path
    for text in expected_in_message:
        assert text in results[0].message
    for text in expected_not_in_message:
        assert text not in results[0].message


@pytest.mark.parametrize("schema_content", [None, {}, ["not", "a", "dict"]])
def test_ModelingRuleSchemaDescriptionsValidator_no_usable_schema(schema_content):
    """
    Given:
        - A modeling rule whose schema file is missing, empty or not a JSON object.
    When:
        - run ModelingRuleSchemaDescriptionsValidator().obtain_invalid_content_items method
    Then:
        - Ensure no ValidationResult is returned (a missing schema is reported by MR100).
    """
    modeling_rule = create_modeling_rule_object()
    modeling_rule.schema_file.file_content = schema_content
    assert not ModelingRuleSchemaDescriptionsValidator().obtain_invalid_content_items(
        [modeling_rule]
    )


@pytest.mark.parametrize(
    "execution_mode, expected_should_run",
    [
        (ExecutionMode.USE_GIT, True),
        (ExecutionMode.ALL_FILES, False),
        (ExecutionMode.SPECIFIC_FILES, False),
    ],
)
def test_ModelingRuleSchemaDescriptionsValidator_runs_only_in_git_mode(
    execution_mode, expected_should_run
):
    """
    Given:
        - A modeling rule.
    When:
        - calling should_run with the different execution modes.
    Then:
        - Ensure the validation runs only in use-git mode, and not with -a or -i.
    """
    modeling_rule = create_modeling_rule_object()
    assert (
        ModelingRuleSchemaDescriptionsValidator().should_run(
            modeling_rule, [], {}, execution_mode
        )
        is expected_should_run
    )
