import pytest

from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.tests.test_tools import create_incident_field_object
from demisto_sdk.commands.validate.validators.IF_validators.IF100_is_valid_name_and_cli_name import (
    IsValidNameAndCliNameValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_incident_field_object(["name", "cliName"], ["case 1", "case1"]),
                create_incident_field_object(["name", "cliName"], ["test 1", "test1"]),
            ],
            1,
            [
                (
                    "The words: case cannot be used as a name.\n"
                    "To fix the problem, remove the words case, "
                    "or add them to the whitelist named argsExceptionsList in:\n"
                    "https://github.com/demisto/server/blob/57fbe417ae420c41ee12a9beb850ff4672209af8/services/servicemodule_test.go#L8273"
                )
            ],
        )
    ]
)
def test_IsValidNameAndCliNameValidator_is_valid(
    content_items: list[IncidentField],
    expected_number_of_failures: int,
    expected_msgs: list[str],
):
    results = IsValidNameAndCliNameValidator().is_valid(content_items=content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )
