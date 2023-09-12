import pytest

from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.hook_validations.correlation_rule import (
    CorrelationRuleValidator,
)
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml

GIT_ROOT = git_path()


def test_no_leading_hyphen():
    """
    Given: A correlation rule with leading hyphen is given.
    When: running no_leading_hyphen.
    Then: Validate that the correlation rule is invalid.
    """
    invalid_correlation_file = f"{GIT_ROOT}/demisto_sdk/commands/common/tests/test_files/invalid_correlation_rule.yml"
    invalid_correlation_yaml = get_yaml(invalid_correlation_file)
    structure_validator = StructureValidator(invalid_correlation_file)
    structure_validator.current_file = invalid_correlation_yaml
    content_validator = ContentEntityValidator(structure_validator)
    correlation_rule_validator = CorrelationRuleValidator(content_validator)

    assert not correlation_rule_validator.no_leading_hyphen()


@pytest.mark.parametrize(
    "execution_mode, search_window, expected_result",
    [
        # Test case 1: Missing 'search_window' when execution_mode is 'SCHEDULED'
        ("SCHEDULED", None, False),
        # Test case 2: Missing 'search_window' when execution_mode is 'REAL_TIME'
        ("REAL_TIME", None, True),
        # Test case 3: Valid 'search_window' when execution_mode is 'SCHEDULED'
        ("SCHEDULED", "valid_window", True),
    ],
)
def test_validate_execution_mode_search_window(
    execution_mode, search_window, expected_result
):
    """
    Given: A correlation rule with execution_mode and search_window.
    When: running validate_execution_mode_search_window.
    Then: Validate the result based on the provided execution_mode and search_window.
    """
    invalid_correlation_file = f"{GIT_ROOT}/demisto_sdk/commands/common/tests/test_files/invalid_correlation_rule_execution_mode.yml"
    invalid_correlation_yaml = get_yaml(invalid_correlation_file)
    structure_validator = StructureValidator(invalid_correlation_file)
    structure_validator.current_file = invalid_correlation_yaml
    content_validator = ContentEntityValidator(structure_validator)
    correlation_rule_validator = CorrelationRuleValidator(content_validator)

    # Set the execution_mode and search_window in the current_file
    correlation_rule_validator.current_file["execution_mode"] = execution_mode
    correlation_rule_validator.current_file["search_window"] = search_window

    result = correlation_rule_validator.validate_execution_mode_search_window()
    assert result == expected_result
