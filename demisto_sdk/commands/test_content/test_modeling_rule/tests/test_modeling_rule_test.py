from pathlib import Path
from uuid import UUID

import junitparser
import pytest
import typer
from freezegun import freeze_time

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger

DEFAULT_TEST_EVENT_ID = UUID("00000000-0000-0000-0000-000000000000")


class ModelingRuleMock:
    path = Path(CONTENT_PATH)

    def normalize_file_name(self):
        return "test_modeling_rule.yml"


class TestVerifyResults:
    def test_verify_results_single_event_matching_expected_outputs(self):
        """
        Given:
            - Simulated query results for one event.
            - Test data for one event, including the expected outputs.

        When:
            - The expected outputs match the simulated query results.

        Then:
            - Verify the function returns True indicating the verification passed.
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            verify_results,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        # Arrange
        tested_dataset = "vendor_product_raw"
        query_results = [
            {
                "vendor_product_raw.test_data_event_id": str(DEFAULT_TEST_EVENT_ID),
                "xdm.field1": "value1",
                "xdm.field2": "value2",
                "xdm.field3": "value3",
            }
        ]
        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset=tested_dataset,
                    event_data={},
                    expected_values={
                        "xdm.field1": "value1",
                        "xdm.field2": "value2",
                        "xdm.field3": "value3",
                    },
                )
            ]
        )
        modeling_rule = ModelingRuleMock()

        try:
            assert verify_results(
                modeling_rule, tested_dataset, query_results, test_data
            )
        except typer.Exit:
            assert False, "No exception should be raised in this scenario."

    def test_verify_results_single_event_non_matching_expected_outputs(self):
        """
        Given:
            - Simulated query results for one event.
            - Test data for one event, including the expected outputs.

        When:
            - The expected outputs do not match the simulated query results.

        Then:
            - Verify the function return False indicating the result not match the expected.
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            verify_results,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        # Arrange
        tested_dataset = "vendor_product_raw"
        query_results = [
            {
                "vendor_product_raw.test_data_event_id": str(DEFAULT_TEST_EVENT_ID),
                "xdm.field1": "value1",
                "xdm.field2": "value2",
                "xdm.field3": "value3",
            }
        ]
        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset=tested_dataset,
                    event_data={},
                    expected_values={
                        "xdm.field1": "value1",
                        "xdm.field2": "value2",
                        "xdm.field3": "value4",
                    },
                )
            ]
        )

        modeling_rule = ModelingRuleMock()
        test_suite = junitparser.TestSuite("Testing")
        test_suite.add_testcases(
            verify_results(modeling_rule, tested_dataset, query_results, test_data)
        )
        assert (
            test_suite.errors + test_suite.failures != 0
        ), "Test modeling rule should fail"


@pytest.mark.parametrize(
    "epoc_time, with_ms, human_readable_time",
    [
        (1686231456000, False, "Jun 8th 2023 13:37:36"),
        (1686231456123, False, "Jun 8th 2023 13:37:36"),
        (1686231456000, True, "Jun 8th 2023 13:37:36.000000"),
        (1686231456123, True, "Jun 8th 2023 13:37:36.123000"),
    ],
)
def test_convert_epoch_time_to_string_time(epoc_time, with_ms, human_readable_time):
    """
    Given:
        - An Epoch time.
            case-1: Epoch time with MS equal to 0. (ignore MS)
            case-2: Epoch time with MS equal to 123. (ignore MS)
            case-3: Epoch time with MS equal to 0.
            case-4: Epoch time with MS equal to 123.

    When:
        - The convert_epoch_time_to_string_time function is running.

    Then:
        - Verify we get the expected results.
    """
    from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
        convert_epoch_time_to_string_time,
    )

    with freeze_time("2023/06/14T10:20:00Z"):
        assert (
            convert_epoch_time_to_string_time(epoc_time, with_ms) == human_readable_time
        )


@pytest.mark.parametrize(
    "day, suffix",
    [
        (1, "st"),
        (2, "nd"),
        (3, "rd"),
        (4, "th"),
        (10, "th"),
        (11, "th"),
        (12, "th"),
        (21, "st"),
        (31, "st"),
    ],
)
def test_day_suffix(day, suffix):
    """
    Given:
        - A day of a month.
            case-1: 1 => st.
            case-2: 2 => nd.
            case-3: 3 => rd.
            case-4: 4 => th.
            case-5: 10 => th.
            case-6: 11 => th.
            case-7: 12 => th.
            case-8: 21 => st.
            case-9: 31 => st.

    When:
        - The day_suffix function is running.

    Then:
        - Verify we get the expected results.
    """
    from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
        day_suffix,
    )

    assert day_suffix(day) == suffix


@pytest.mark.parametrize(
    "mr_text, expected_result",
    [
        ("historically", False),
        ("call a", True),
    ],
)
def test_call_rule_regex(mr_text, expected_result):
    """
    Test the CALL_RULE_REGEX regex matches text containing 'call'.

    Given:
        - mr_text: Text to search for 'call'
        - expected_result: Whether we expect mr_text to match

    When:
        - Search mr_text with ModelingRule.CALL_RULE_REGEX

    Then:
        - The search result should match expected_result
    """
    from demisto_sdk.commands.common.content.objects.pack_objects.modeling_rule.modeling_rule import (
        ModelingRule,
    )

    mr = ModelingRule
    assert bool(mr.CALL_RULE_REGEX.search(mr_text)) == expected_result


class TestValidateSchemaAlignedWithTestData:
    @pytest.mark.parametrize(
        "event_data, schema_file",
        [
            (
                {
                    "int": 1,
                    "string": "2",
                    "bool": True,
                    "float": 1.0,
                    "datetime": "Nov 9th 2022 15:46:30",
                    "json": {"1": "2"},
                },
                {
                    "dataset": {
                        "int": {"type": "int", "is_array": False},
                        "string": {"type": "string", "is_array": False},
                        "float": {"type": "float", "is_array": False},
                        "datetime": {"type": "datetime", "is_array": False},
                        "bool": {"type": "boolean", "is_array": False},
                    }
                },
            ),
            (
                {
                    "list_int": [1, 2],
                    "list_string": ["1", "2"],
                    "list_bool": [True, False],
                    "list_float": [1.0, 2.0],
                    "list_datetime": ["Nov 9th 2022 15:46:30", "Nov 9th 2022 15:46:30"],
                    "list_json": [{"1": "2"}, {"1": "2"}],
                },
                {
                    "dataset": {
                        "list_int": {"type": "string", "is_array": False},
                        "list_string": {"type": "string", "is_array": False},
                        "list_float": {"type": "string", "is_array": False},
                        "list_datetime": {"type": "string", "is_array": False},
                        "list_bool": {"type": "string", "is_array": False},
                        "list_json": {"type": "string", "is_array": False},
                    }
                },
            ),
        ],
    )
    def test_validate_schema_aligned_with_test_data_positive(
        self, mocker, event_data: dict, schema_file: dict
    ):
        """
        Given:
            - Case A: event data with all schema types and correct corresponding schema file
            - Case B: event data with all schema types as lists and correct corresponding schema file

        When:
            - running validate_schema_aligned_with_test_data.

        Then:
            - verify no exception is raised.
            - verify that there was not error raised
            - verify not warning was raised
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            validate_schema_aligned_with_test_data,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        logger_error_mocker = mocker.patch.object(logger, "error")
        logger_warning_mocker = mocker.patch.object(logger, "warning")

        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset="dataset",
                    event_data=event_data,
                    expected_values={},
                )
            ]
        )

        validate_schema_aligned_with_test_data(test_data=test_data, schema=schema_file)
        assert not logger_error_mocker.called
        assert not logger_warning_mocker.called

    def test_validate_schema_aligned_with_test_data_missing_fields_in_test_data(
        self, mocker
    ):
        """
        Given:
            - event data that is missing one schema field.

        When:
            - running validate_schema_aligned_with_test_data.

        Then:
            - verify no exception is raised.
            - verify that there was not error raised
            - verify that warning was raised indicating that the test data is missing schema field
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            validate_schema_aligned_with_test_data,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        logger_error_mocker = mocker.patch.object(logger, "error")
        logger_warning_mocker = mocker.patch.object(logger, "warning")

        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset="dataset",
                    event_data={"int": 1},
                    expected_values={},
                )
            ]
        )

        validate_schema_aligned_with_test_data(
            test_data=test_data,
            schema={
                "dataset": {
                    "int": {"type": "int", "is_array": False},
                    "string": {"type": "string", "is_array": False},
                }
            },
        )
        assert not logger_error_mocker.called
        assert logger_warning_mocker.called

    def test_validate_schema_aligned_with_test_data_invalid_schema_mappings(
        self, mocker
    ):
        """
        Given:
            - event data that it's mapping to schema is wrong.

        When:
            - running validate_schema_aligned_with_test_data.

        Then:
            - verify 'Typer.exception' is raised.
            - verify that there was not warning raised
            - verify that error was raised indicating that the test data is missing schema field
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            validate_schema_aligned_with_test_data,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        logger_error_mocker = mocker.patch.object(logger, "error")
        logger_warning_mocker = mocker.patch.object(logger, "warning")

        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset="dataset",
                    event_data={"int": 1, "bool": True},
                    expected_values={},
                )
            ]
        )

        success, _ = validate_schema_aligned_with_test_data(
            test_data=test_data,
            schema={
                "dataset": {
                    "int": {"type": "string", "is_array": False},
                    "bool": {"type": "float", "is_array": False},
                }
            },
        )
        assert success is False
        assert logger_error_mocker.called
        assert not logger_warning_mocker.called

    def test_validate_schema_aligned_with_test_data_events_have_same_key_with_different_types(
        self, mocker
    ):
        """
        Given:
            - 2 events that have the same key with two different types (int and string).

        When:
            - running validate_schema_aligned_with_test_data.

        Then:
            - verify no exception is raised.
            - verify that the correct message is printed to logger info.
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import (
            validate_schema_aligned_with_test_data,
        )
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
            EventLog,
            TestData,
        )

        logger_error_mocker = mocker.patch.object(logger, "error")
        logger_warning_mocker = mocker.patch.object(logger, "warning")

        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset="dataset",
                    event_data={"int": 1, "bool": True},
                    expected_values={},
                ),
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor="vendor",
                    product="product",
                    dataset="dataset",
                    event_data={"int": "1", "bool": True},
                    expected_values={},
                ),
            ]
        )

        success, _ = validate_schema_aligned_with_test_data(
            test_data=test_data,
            schema={
                "dataset": {
                    "int": {"type": "int", "is_array": False},
                    "bool": {"type": "boolean", "is_array": False},
                }
            },
        )
        assert success is False
        assert (
            "The testdata contains events with the same event_key"
            in logger_error_mocker.call_args_list[0].args[0]
        )
        assert not logger_warning_mocker.called
