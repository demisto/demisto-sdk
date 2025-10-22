import pytest
from demisto_sdk.commands.validate.tests.test_tools import (
    create_script_object,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS_100_aggregated_script_has_tpb import (
    AggregatedScriptHasTPBValidator,
    MISSING_TPB_MESSAGE,
    NO_TESTS_FORMAT,
)

class TestAggregatedScriptHasTPBValidator:
    """Test suite for AggregatedScriptHasTPBValidator."""

    @pytest.fixture
    def validator(self) -> AggregatedScriptHasTPBValidator:
        """Return an instance of the validator for testing."""
        return AggregatedScriptHasTPBValidator()

    def test_valid_script_with_tpb(self, validator: AggregatedScriptHasTPBValidator) -> None:
        """
        Given: A script with a test playbook
        When: Validating the script
        Then: No validation errors should be returned
        """
        # Arrange
        content_items = [create_script_object()]  # example script has a testing tpb

        # Act
        results = validator.obtain_invalid_content_items(content_items)

        # Assert
        assert len(results) == 0

    def test_script_without_tests(self, validator: AggregatedScriptHasTPBValidator) -> None:
        """
        Given: A script with no test playbooks
        When: Validating the script
        Then: A validation error should be returned
        """
        # Arrange
        script_name = "test_script"
        content_items = [
            create_script_object(
                paths=["tests", "name"],
                values=[[], script_name],
            )
        ]

        # Act
        results = validator.obtain_invalid_content_items(content_items)

        # Assert
        assert len(results) == 1
        assert results[0].message == MISSING_TPB_MESSAGE.format(name=script_name)

    @pytest.mark.parametrize(
        "test_value,expected_errors",
        [
            ([], 1),  # Empty tests list
            (NO_TESTS_FORMAT, 1),  # No tests auto-formatted
            (["TestPlaybook"], 0),  # Valid test playbook
            (["TestPlaybook1", "TestPlaybook2"], 0),  # Multiple test playbooks
        ],
    )
    def test_various_test_conditions(
        self,
        validator: AggregatedScriptHasTPBValidator,
        test_value,
        expected_errors: int,
    ) -> None:
        """
        Given: A script with various test playbook conditions
        When: Validating the script
        Then: The appropriate number of validation errors should be returned
        """
        # Arrange
        content_items = [
            create_script_object(
                paths=["tests"],
                values=[test_value],
            )
        ]

        # Act
        results = validator.obtain_invalid_content_items(content_items)

        # Assert
        assert len(results) == expected_errors

    def test_multiple_scripts_validation(self, validator: AggregatedScriptHasTPBValidator) -> None:
        """
        Given: Multiple scripts with different test conditions
        When: Validating all scripts
        Then: Only scripts without test playbooks should be marked as invalid
        """
        # Arrange
        valid_script = create_script_object()
        invalid_script = create_script_object(
            paths=["tests", "name"],
            values=[[], "invalid_script"],
        )
        content_items = [valid_script, invalid_script]

        # Act
        results = validator.obtain_invalid_content_items(content_items)

        # Assert
        assert len(results) == 1
        assert results[0].content_object == invalid_script
