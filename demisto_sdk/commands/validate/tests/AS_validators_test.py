import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS_100_aggregated_script_has_tpb import (
    AGGREGATED_SCRIPTS_PACK_NAME,
    MISSING_TPB_MESSAGE,
    NO_TESTS_FORMAT,
    AggregatedScriptHasTPBValidator,
)
from TestSuite.repo import ChangeCWD


class TestAggregatedScriptHasTPBValidator:
    """Test suite for AggregatedScriptHasTPBValidator."""

    @pytest.fixture
    def validator(self) -> AggregatedScriptHasTPBValidator:
        """Return an instance of the validator for testing."""
        return AggregatedScriptHasTPBValidator()

    def test_valid_script_with_tpb(
        self, validator: AggregatedScriptHasTPBValidator
    ) -> None:
        """
        Given: A script with a test playbook in the AggregatedScripts pack
        When: Validating the script
        Then: No validation errors should be returned
        """
        # Arrange
        with ChangeCWD(REPO.path):
            content_items = [
                create_script_object(pack_info={"name": AGGREGATED_SCRIPTS_PACK_NAME})
            ]  # example script has a testing tpb

            # Act
            results = validator.obtain_invalid_content_items(content_items)

            # Assert
            assert len(results) == 0

    def test_script_without_tests(
        self, validator: AggregatedScriptHasTPBValidator
    ) -> None:
        """
        Given: A script with no test playbooks in the AggregatedScripts pack
        When: Validating the script
        Then: A validation error should be returned
        """
        # Arrange
        with ChangeCWD(REPO.path):
            script_name = "test_script"
            content_items = [
                create_script_object(
                    paths=["tests", "name"],
                    values=[[], script_name],
                    pack_info={"name": AGGREGATED_SCRIPTS_PACK_NAME},
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
        Given: A script in the AggregatedScripts pack with various test playbook conditions
        When: Validating the script
        Then: The appropriate number of validation errors should be returned
        """
        # Arrange
        with ChangeCWD(REPO.path):
            script = create_script_object(
                paths=["tests"],
                values=[test_value],
                pack_info={"name": AGGREGATED_SCRIPTS_PACK_NAME},
            )
            content_items = [script]

            # Act
            results = validator.obtain_invalid_content_items(content_items)

            # Assert
            assert len(results) == expected_errors

    def test_script_in_different_pack(
        self, validator: AggregatedScriptHasTPBValidator
    ) -> None:
        """
        Given: A script in a different pack than AggregatedScripts
        When: Validating the script
        Then: No validation errors should be returned
        """
        # Arrange
        content_items = [create_script_object(paths=["tests"], values=[[]])]

        # Act
        results = validator.obtain_invalid_content_items(content_items)

        # Assert
        assert len(results) == 0

    def test_multiple_scripts_validation(
        self, validator: AggregatedScriptHasTPBValidator
    ) -> None:
        """
        Given: Multiple scripts in the AggregatedScripts pack with different test conditions
        When: Validating all scripts
        Then: Only scripts without test playbooks should be marked as invalid
        """
        # Arrange
        with ChangeCWD(REPO.path):
            valid_script = create_script_object(
                pack_info={"name": AGGREGATED_SCRIPTS_PACK_NAME}
            )
            invalid_script = create_script_object(
                paths=["tests", "name"],
                values=[[], "invalid_script"],
                pack_info={"name": AGGREGATED_SCRIPTS_PACK_NAME},
            )
            content_items = [valid_script, invalid_script]

            # Act
            results = validator.obtain_invalid_content_items(content_items)

            # Assert
            assert len(results) == 1
            assert results[0].content_object == invalid_script
