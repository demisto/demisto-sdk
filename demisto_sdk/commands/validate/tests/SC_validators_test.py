from demisto_sdk.commands.validate.tests.test_tools import (
    create_script_object,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC105_incident_not_in_args_validator import (
    IsScriptArgumentsContainIncidentWordValidator,
)


def test_IsScriptArgumentsContainIncidentWordValidator_is_valid():
    """
    Given:
     - 1 script that has the word incident in its arguments and is not deprecated
     - 1 script that has the word incident in its arguments and is deprecated
     - 1 script that does not have the word incident in its arguments

    When:
     - Running the IsScriptArgumentsContainIncidentWordValidator validator

    Then:
     - make sure the script with the argument that has "incident" fails the validation
    """
    content_items = (
        create_script_object(
            paths=["name", "args"],
            values=["InvalidScript", [{"name": "incident-id", "description": "test"}]],
        ),
        create_script_object(
            paths=["args"],
            values=[
                [{"name": "incident-id", "description": "test", "deprecated": True}]
            ],
        ),
        create_script_object(),
    )

    results = IsScriptArgumentsContainIncidentWordValidator().is_valid(content_items)
    assert len(results) == 1
    assert results[0].content_object.name == "InvalidScript"
