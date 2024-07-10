from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
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
        Calling Validate
    Then:
        The validation should fail
    """
    correlation_rule = create_correlation_rule_object()
    assert len(ExecutionModeSearchWindowValidator().is_valid([correlation_rule])) == 1
    

def test_validate_execution_mode_search_window_with_empty_search_window():
    """
    Given:
        A correlation rule with empty search_window but execution_mode == SCHEDULED.
    When:
        Calling Validate
    Then:
        The validation should fail
    """
    correlation_rule = create_correlation_rule_object(
        ["execution_mode", "search_window"],
        ["SCHEDULED", ""]
    )
    assert len(ExecutionModeSearchWindowValidator().is_valid([correlation_rule])) == 1



def test_validate_execution_mode_search_window_with_null_search_window():
    """
    Given:
        A correlation rule with empty search_window but execution_mode == SCHEDULED.
    When:
        Calling Validate
    Then:
        The validation should fail
    """
    correlation_rule = create_correlation_rule_object(
        ["execution_mode", "search_window"],
        ["REAL_TIME", None]
    )
    assert len(ExecutionModeSearchWindowValidator().is_valid([correlation_rule])) == 0
