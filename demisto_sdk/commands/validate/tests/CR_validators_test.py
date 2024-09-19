from demisto_sdk.commands.validate.tests.test_tools import (
    create_correlation_rule_object,
)
from demisto_sdk.commands.validate.validators.CR_validators.CR102_validate_execution_mode_search_window import (
    ExecutionModeSearchWindowValidator,
)


def test_validate_execution_mode_search_window_with_no_fields():
    """
    Given:
        An default correlation rule with no search_window and execution_mode fields.
    When:
        Calling Validate.
    Then:
        The validation should fail.
    """
    correlation_rule = create_correlation_rule_object()
    assert (
        len(
            ExecutionModeSearchWindowValidator().obtain_invalid_content_items(
                [correlation_rule]
            )
        )
        == 1
    )


def test_validate_execution_mode_search_window_with_empty_search_window():
    """
    Given:
        A correlation rule with empty search_window but execution_mode == SCHEDULED.
    When:
        Calling Validate.
    Then:
        The validation should fail.
    """
    correlation_rule = create_correlation_rule_object(
        ["execution_mode", "search_window"], ["SCHEDULED", ""]
    )
    assert (
        len(
            ExecutionModeSearchWindowValidator().obtain_invalid_content_items(
                [correlation_rule]
            )
        )
        == 1
    )


def test_validate_execution_mode_search_window_with_not_defined_search_window():
    """
    Given:
        A correlation rule with not defined search_window but execution_mode == SCHEDULED.
    When:
        Calling Validate.
    Then:
        The validation should fail.
    """
    correlation_rule = create_correlation_rule_object(["execution_mode"], ["SCHEDULED"])
    assert (
        len(
            ExecutionModeSearchWindowValidator().obtain_invalid_content_items(
                [correlation_rule]
            )
        )
        == 1
    )


def test_validate_execution_mode_search_window_with_null_search_window():
    """
    Given:
        A correlation rule with search_window == None but execution_mode == SCHEDULED.
    When:
        Calling Validate.
    Then:
        The validation shouldn't fail.
    """
    correlation_rule = create_correlation_rule_object(
        ["execution_mode", "search_window"], ["REAL_TIME", None]
    )
    assert (
        len(
            ExecutionModeSearchWindowValidator().obtain_invalid_content_items(
                [correlation_rule]
            )
        )
        == 0
    )
