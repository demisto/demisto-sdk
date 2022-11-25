from uuid import UUID
import pytest
import typer


DEFAULT_TEST_EVENT_ID = UUID('00000000-0000-0000-0000-000000000000')


class TestVerifyResults:

    def test_verify_results_single_event_matching_expected_outputs(self):
        """
        Given:
            - Simulated query results for one event.
            - Test data for one event, including the expected outputs.
        
        When:
            - The expected outputs match the simulated query results.

        Then:
            - Verify the function returns successfully.
        """
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData, EventLog
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import verify_results
        # Arrange
        query_results = [
            {
                'vendor_product_raw.test_data_event_id': str(DEFAULT_TEST_EVENT_ID),
                'xdm.field1': 'value1',
                'xdm.field2': 'value2',
                'xdm.field3': 'value3',
            }
        ]
        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor='vendor',
                    product='product',
                    dataset='vendor_product_raw',
                    event_data={},
                    expected_values={
                        'xdm.field1': 'value1',
                        'xdm.field2': 'value2',
                        'xdm.field3': 'value3',
                    }
                )
            ]
        )

        try:
            verify_results(query_results, test_data)
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
            - Verify the function raises a typer.Exit exception.
        """
        from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData, EventLog
        from demisto_sdk.commands.test_content.test_modeling_rule.test_modeling_rule import verify_results
        # Arrange
        query_results = [
            {
                'vendor_product_raw.test_data_event_id': str(DEFAULT_TEST_EVENT_ID),
                'xdm.field1': 'value1',
                'xdm.field2': 'value2',
                'xdm.field3': 'value3',
            }
        ]
        test_data = TestData(
            data=[
                EventLog(
                    test_data_event_id=DEFAULT_TEST_EVENT_ID,
                    vendor='vendor',
                    product='product',
                    dataset='vendor_product_raw',
                    event_data={},
                    expected_values={
                        'xdm.field1': 'value1',
                        'xdm.field2': 'value2',
                        'xdm.field3': 'value4',
                    }
                )
            ]
        )

        with pytest.raises(typer.Exit):
            verify_results(query_results, test_data)
