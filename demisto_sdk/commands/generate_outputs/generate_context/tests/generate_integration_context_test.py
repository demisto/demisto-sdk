import os

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml, write_dict

# Test data files
FAKE_INTEGRATION_YML = get_yaml(
    f"{git_path()}/demisto_sdk/commands/generate_outputs/generate_context/tests/test_data/fake_integration_empty_output.yml"
)

FAKE_OUTPUT_CONTEXTS = [
    {"contextPath": "File.SHA256", "description": "", "type": "String"},
    {"contextPath": "File.SHA1", "description": "", "type": "String"},
    {"contextPath": "File.MD5", "description": "", "type": "String"},
    {"contextPath": "File.Name", "description": "", "type": "String"},
    {"contextPath": "File.Date", "description": "", "type": "Date"},
    {"contextPath": "File.Size", "description": "", "type": "Number"},
    {"contextPath": "File.Check", "description": "", "type": "Boolean"},
    {"contextPath": "File.Type", "description": "", "type": "Unknown"},
    {"contextPath": "File.EntryID", "description": "", "type": "String"},
    {"contextPath": "File.SSDeep", "description": "", "type": "String"},
]

FAKE_OUTPUTS_1 = {
    "File": {
        "SHA256": "111",
        "SHA1": "111",
        "MD5": "111",
        "Name": "111",
        "Date": "2018-09-02T23:05:12Z",
    }
}
FAKE_OUTPUTS_2 = {
    "File": {
        "Date": "2018-09-02T23:05:12Z",
        "Size": 111,
        "Check": True,
        "Type": None,
        "EntryID": "111",
        "SSDeep": "111",
    }
}

FAKE_EXAMPLES_FILE = f"{git_path()}/commands/demisto_sdk/generate_outputs/generate_context/tests/test_data/fake_examples.txt"


def test_generate_context_from_outputs():
    """
    Given
        - A string representing an example output json
    When
        - generating context objects
    Then
        - Ensure the outputs are correct
    """
    from demisto_sdk.commands.generate_outputs.generate_context.generate_integration_context import (
        dict_from_outputs_str,
    )

    EXAMPLE_INT_OUTPUTS = """{"Guardicore": {"Endpoint": {"asset_id": "1-2-3-4-5",
                                "ip_addresses": ["1.1.1.1",
                                              "ffe::fef:fefe:fefee:fefe"],
                                "last_seen": 1629200550561,
                                "name": "Accounting-web-1",
                                "status": 1,
                                "tenant_name": "esx10/lab_a/Apps/Accounting"}}}"""

    assert dict_from_outputs_str(
        "!some-test-command=172.16.1.111", EXAMPLE_INT_OUTPUTS
    ) == {
        "arguments": [],
        "name": "some-test-command=172.16.1.111",
        "outputs": [
            {
                "contextPath": "Guardicore.Endpoint.asset_id",
                "description": "",
                "type": "String",
            },
            {
                "contextPath": "Guardicore.Endpoint.ip_addresses",
                "description": "",
                "type": "String",
            },
            {
                "contextPath": "Guardicore.Endpoint.last_seen",
                "description": "",
                "type": "Date",
            },
            {
                "contextPath": "Guardicore.Endpoint.name",
                "description": "",
                "type": "String",
            },
            {
                "contextPath": "Guardicore.Endpoint.status",
                "description": "",
                "type": "Number",
            },
            {
                "contextPath": "Guardicore.Endpoint.tenant_name",
                "description": "",
                "type": "String",
            },
        ],
    }


def test_insert_outputs(mocker):
    """
    Given
      - A yaml file and fake example outputs
    When
      - inserting those examples into the yml
    Then
      - Ensure the outputs are inserted correctly
    """
    from demisto_sdk.commands.generate_outputs.generate_context import (
        generate_integration_context,
    )

    command_name = "zoom-fetch-recording"
    mocker.patch.object(
        generate_integration_context,
        "build_example_dict",
        return_value=(
            {
                command_name: [
                    (None, None, json.dumps(FAKE_OUTPUTS_1)),
                    (None, None, json.dumps(FAKE_OUTPUTS_2)),
                ]
            },
            [],
        ),
    )

    yml_data = FAKE_INTEGRATION_YML

    yml_data = generate_integration_context.insert_outputs(
        yml_data, command_name, FAKE_OUTPUT_CONTEXTS
    )
    for command in yml_data["script"]["commands"]:
        if command.get("name") == command_name:
            assert command["outputs"] == FAKE_OUTPUT_CONTEXTS
            break
    else:
        raise AssertionError(f"No command {command_name} in yml_data)")


def test_generate_integration_context(mocker, tmpdir):
    """
    Given
      - A yaml file and fake example file
    When
      - generating the yml ouputs from the examples
    Then
      - Ensure the outputs are inserted correctly
    """
    from demisto_sdk.commands.generate_outputs.generate_context import (
        generate_integration_context,
    )

    command_name = "zoom-fetch-recording"
    mocker.patch.object(
        generate_integration_context,
        "build_example_dict",
        return_value=(
            {
                command_name: [
                    (None, None, json.dumps(FAKE_OUTPUTS_1)),
                    (None, None, json.dumps(FAKE_OUTPUTS_2)),
                ]
            },
            [],
        ),
    )

    # Temp file to check
    filename = os.path.join(tmpdir.strpath, "fake_integration.yml")
    write_dict(filename, FAKE_INTEGRATION_YML)

    # Make sure that there are no outputs
    yml_data = get_yaml(filename)
    for command in yml_data["script"]["commands"]:
        if command.get("name") == command_name:
            command["outputs"] = ""
            break
    else:
        raise AssertionError(f"command {command_name} is not found in yml_data")

    generate_integration_context.generate_integration_context(
        filename, FAKE_EXAMPLES_FILE
    )

    # Check we have new data
    yml_data = get_yaml(filename)
    for command in yml_data["script"]["commands"]:
        if command.get("name") == command_name:
            assert command["outputs"] == FAKE_OUTPUT_CONTEXTS
            break
    else:
        raise AssertionError(f"command {command_name} is not found in yml_data")
