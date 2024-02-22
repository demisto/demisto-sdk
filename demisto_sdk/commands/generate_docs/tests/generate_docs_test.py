import inspect
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
from pytest_mock import MockerFixture

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (
    INTEGRATIONS_README_FILE_NAME,
)
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.markdown_lint import run_markdownlint
from demisto_sdk.commands.common.tools import get_json, get_yaml

# from demisto_sdk.commands.run_cmd.runner import Runner
from demisto_sdk.commands.generate_docs import common
from demisto_sdk.commands.generate_docs.generate_integration_doc import (
    append_or_replace_command_in_docs,
    disable_md_autolinks,
    generate_commands_section,
    generate_integration_doc,
    generate_mirroring_section,
    generate_setup_section,
    generate_single_command_section,
    get_command_examples,
)
from demisto_sdk.commands.generate_docs.generate_playbook_doc import (
    generate_playbook_doc,
)
from TestSuite.pack import Pack
from TestSuite.repo import Repo

FILES_PATH = os.path.normpath(
    os.path.join(__file__, git_path(), "demisto_sdk", "tests", "test_files")
)
FAKE_ID_SET = get_json(os.path.join(FILES_PATH, "fake_id_set.json"))
TEST_PLAYBOOK_PATH = os.path.join(FILES_PATH, "playbook-Test_playbook.yml")
PLAYBOOK_PATH = os.path.join(FILES_PATH, "beta-playbook-valid.yml")
TEST_SCRIPT_PATH = os.path.join(FILES_PATH, "script-test_script.yml")
TEST_INTEGRATION_PATH = os.path.join(
    FILES_PATH, "fake_integration/fake_integration.yml"
)
TEST_INTEGRATION_2_PATH = os.path.join(
    FILES_PATH,
    "integration-display-credentials-none/integration-display" "-credentials-none.yml",
)

DEMISTO_SDK_PATH = os.path.join(git_path(), "demisto_sdk")
TEST_FILES = os.path.join(
    DEMISTO_SDK_PATH, "commands", "generate_docs", "tests", "test_files"
)

yaml = YAML_Handler()

# common tests


def test_format_md():
    """
    Given
        - A string representing a markdown returned from server with <br> tag

    When
        - generating docs

    Then
        - Ensure all <br> <BR> tags in markdown replaced with <br/> tags
    """
    from demisto_sdk.commands.generate_docs.common import format_md

    md_returned_from_server = """
    ### Domain List
    |Malicious|Name|
    |---|---|
    | Vendor: HelloWorld<br>Description: Hello World returned reputation 88 | google.com |
    | Vendor: HelloWorld<BR>Description: Hello World returned reputation 88 | google.com |
    """
    res = format_md(md_returned_from_server)
    expected_res = """
    ### Domain List
    |Malicious|Name|
    |---|---|
    | Vendor: HelloWorld<br/>Description: Hello World returned reputation 88 | google.com |
    | Vendor: HelloWorld<br/>Description: Hello World returned reputation 88 | google.com |
    """
    assert expected_res == res
    # mixed case test
    assert "<bR>" not in format_md("test<bR>")
    assert "<HR>" not in format_md("test<HR>")
    # these are a valid but we replace for completeness
    assert format_md("test<br></br>\nthis<br>again").count("<br/>") == 2
    assert format_md("test<hr></hr>\nthis<hr>again").count("<hr/>") == 2
    # test removing style
    assert "style=" not in format_md(
        '<div style="background:#eeeeee; border:1px solid #cccccc; padding:5px 10px">"this is a test"</div>'
    )


def test_string_escape_md():
    from demisto_sdk.commands.generate_docs.common import string_escape_md

    res = string_escape_md(
        "First fetch timestamp (<number> <time unit>, e.g., 12 hours, 7 days)",
        minimal_escaping=True,
        escape_multiline=True,
        escape_less_greater_signs=True,
    )
    assert (
        res
        == "First fetch timestamp (`<number>` `<time unit>`, e.g., 12 hours, 7 days)"
    )

    res = string_escape_md(
        "format: <number> <time unit>, e.g., 12 hours, 7 days.",
        minimal_escaping=True,
        escape_multiline=True,
        escape_less_greater_signs=True,
    )
    assert res == "format: `<number>` `<time unit>`, e.g., 12 hours, 7 days."

    res = string_escape_md("new line test \n", escape_multiline=True)
    assert "\n" not in res
    assert "<br/>" in res

    res = string_escape_md('Here are "Double Quotation" marks')
    assert '"' in res

    res = string_escape_md("Here are 'Single Quotation' marks")
    assert "'" in res

    res = string_escape_md(
        "- This _sentence_ has _wrapped_with_underscore_ and _another_ words."
    )
    assert "\\_wrapped_with_underscore\\_" in res
    assert "\\_sentence\\_" in res
    assert "\\_another\\_" in res
    assert res.startswith("\\-")


def test_generate_list_section_empty():
    from demisto_sdk.commands.generate_docs.common import generate_list_section

    section = generate_list_section("Inputs", [], empty_message="No inputs found.")

    expected_section = ["## Inputs", "", "No inputs found.", ""]

    assert section == expected_section


def test_generate_numbered_section():
    from demisto_sdk.commands.generate_docs.common import generate_numbered_section

    section = generate_numbered_section("Use Cases", "* Drink coffee. * Write code.")

    expected_section = ["## Use Cases", "", "1. Drink coffee.", "2. Write code.", ""]

    assert section == expected_section


def test_generate_list_section():
    from demisto_sdk.commands.generate_docs.common import generate_list_section

    section = generate_list_section(
        "Inputs", ["item1", "item2"], False, "No inputs found."
    )

    expected_section = ["## Inputs", "", "* item1", "* item2", ""]

    assert section == expected_section


def test_generate_list_with_text_section():
    from demisto_sdk.commands.generate_docs.common import generate_list_section

    section = generate_list_section(
        "Inputs", ["item1", "item2"], True, "No inputs found.", "some text"
    )

    expected_section = [
        "## Inputs",
        "",
        "---",
        "some text",
        "",
        "* item1",
        "* item2",
        "",
    ]

    assert section == expected_section


TEST_TABLE_SECTION_EMPTY = [
    (
        [],
        "Script Data",
        "No data found.",
        "This is the metadata of the script.",
        ["## Script Data", "", "---", "No data found.", ""],
    ),
    ([], "Script Data", "", "", [""]),
    ([], "Script Data", "", "This is the metadata of the script.", [""]),
]


@pytest.mark.parametrize(
    "data, title, empty_message, text, expected_result", TEST_TABLE_SECTION_EMPTY
)
def test_generate_table_section_empty(
    data, title, empty_message, text, expected_result
):
    """Unit test
    Given
    - Case 1: script empty metadata - an empty list instead of a list containing dicts with data to generate the tables from,
    title - the table header, empty message to replace with the table if no data is given and text -
    the text to add under the header if data is given.
    - Case 2: script empty metadata, script title.
    - Case 3: script empty metadata, script title, text.
    When
    - running the generate_table_section command on the inputs
    Then
    - Validate That the section was created correctly.
    - Case 1: Table section with title and empty_message instead of a table.
    - Case 2: No section is created.
    - Case 3: No section is created.
    """
    from demisto_sdk.commands.generate_docs.common import generate_table_section

    section = generate_table_section(data, title, empty_message, text)

    assert section == expected_result


def test_generate_table_section():
    """Unit test
    Given
    - generate_table_section command
    - script metadata as a list of dicts
    When
    - running the command on the inputs including a docker image
    Then
    - Validate That the script metadata was created correctly.
    """
    from demisto_sdk.commands.generate_docs.common import generate_table_section

    section = generate_table_section(
        [{"Type": "python2", "Docker Image": "demisto/python2"}],
        "Script Data",
        "No data found.",
        "This is the metadata of the script.",
    )

    expected_section = [
        "## Script Data",
        "",
        "---",
        "This is the metadata of the script.",
        "| **Type** | **Docker Image** |",
        "| --- | --- |",
        "| python2 | demisto/python2 |",
        "",
    ]

    assert section == expected_section


def test_generate_table_section_with_newlines():
    """Unit test
    Given
    - generate_table_section command
    - inputs as a list of dicts
    When
    - running the command on an input including \n (PcapFilter)
    Then
    - Validate That the \n is escaped correctly in a markdown format.
    """
    from demisto_sdk.commands.generate_docs.common import generate_table_section

    section = generate_table_section(
        [
            {
                "Name": "RsaDecryptKeyEntryID",
                "Description": "This input specifies the file entry id for the RSA decrypt key if the user provided the key"
                " in the incident.",
                "Default Value": "File.EntryID",
                "Required": "Optional",
            },
            {
                "Name": "PcapFileEntryID",
                "Description": "This input specifies the file entry id for the PCAP file if the user provided the file in the"
                " incident. One PCAP file can run per incident.",
                "Default Value": "File.EntryID",
                "Required": "Optional",
            },
            {
                "Name": "WpaPassword",
                "Description": "This input value is used to provide a WPA \\(Wi\\-Fi Protected Access\\) password to decrypt"
                " encrypted 802.11 Wi\\-FI traffic.",
                "Default Value": "",
                "Required": "Optional",
            },
            {
                "Name": "PcapFilter",
                "Description": "This input specifies a search filter to be used on the PCAP file. Filters can be used to"
                " search only for a specific IP, protocols and other examples. The syntax is the same as in"
                " Wireshark which can be found here:"
                " https://www.wireshark.org/docs/man-pages/wireshark-filter.html \nFor this playbook, using"
                " a PCAP filter will generate a new smaller PCAP file based on the provided filter therefor"
                " thus reducing the extraction of non relevant files.",
                "Default Value": "",
                "Required": "Optional",
            },
            {
                "Name": "ExtractedFilesLimit",
                "Description": "This input limits the number of files to be extracted from the PCAP file."
                " Default value is 5.",
                "Default Value": "5",
                "Required": "Optional",
            },
        ],
        "Playbook Inputs",
        "There are no inputs for this playbook.",
    )

    expected_section = [
        "## Playbook Inputs",
        "",
        "---",
        "",
        "| **Name** | **Description** | **Default Value** | **Required** |",
        "| --- | --- | --- | --- |",
        "| RsaDecryptKeyEntryID | This input specifies the file entry id for the RSA decrypt key if the user provided"
        " the key in the incident. | File.EntryID | Optional |",
        "| PcapFileEntryID | This input specifies the file entry id for the PCAP file if the user provided the file in"
        " the incident. One PCAP file can run per incident. | File.EntryID | Optional |",
        "| WpaPassword | This input value is used to provide a WPA \\(Wi\\-Fi Protected Access\\) password"
        " to decrypt encrypted 802.11 Wi\\-FI traffic. |  | Optional |",
        "| PcapFilter | This input specifies a search filter to be used on the PCAP file. Filters can be used to"
        " search only for a specific IP, protocols and other examples. The syntax is the same as in Wireshark which"
        " can be found here: https://www.wireshark.org/docs/man-pages/wireshark-filter.html <br/>For this"
        " playbook, using a PCAP filter will generate a new smaller PCAP file based on the provided filter therefor"
        " thus reducing the extraction of non relevant files. |  | Optional |",
        "| ExtractedFilesLimit | This input limits the number of files to be extracted from the PCAP file. "
        "Default value is 5. | 5 | Optional |",
        "",
    ]

    assert section == expected_section


# playbook tests


def test_get_inputs():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import get_inputs

    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    inputs, errors = get_inputs(playbook)

    expected_query = (
        "(type:ip or type:file or type:Domain or type:URL) -tags:pending_review "
        "and (tags:approved_black or tags:approved_white or tags:approved_watchlist)"
    )
    expected_inputs = [
        {
            "Name": "InputA",
            "Description": "",
            "Default Value": "File.Name",
            "Required": "Optional",
        },
        {
            "Name": "InputB",
            "Description": "This is input b",
            "Default Value": "johnnydepp@gmail.com",
            "Required": "Required",
        },
        {
            "Name": "InputC",
            "Description": "",
            "Default Value": "No_Accessor",
            "Required": "Optional",
        },
        {
            "Name": "Indicator Query",
            "Description": "Indicators matching the indicator query will be used as playbook input",
            "Default Value": expected_query,
            "Required": "Optional",
        },
        {
            "Name": "InputD",
            "Description": "test & description",
            "Default Value": "File.NameD",
            "Required": "Optional",
        },
    ]

    assert inputs == expected_inputs
    assert errors[0] == "Error! You are missing description in playbook input InputA"


def test_get_outputs():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import get_outputs

    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    outputs, errors = get_outputs(playbook)

    expected_outputs = [
        {
            "Path": "Email.To",
            "Description": "The recipient of the email.",
            "Type": "string",
        },
        {"Path": "FileData", "Description": "", "Type": "string"},
        {
            "Path": "Email.From",
            "Description": "The sender & of the email.",
            "Type": "string",
        },
    ]

    assert outputs == expected_outputs
    assert errors[0] == "Error! You are missing description in playbook output FileData"


def test_get_playbook_dependencies():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import (
        get_playbook_dependencies,
    )

    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    playbooks, integrations, scripts, commands = get_playbook_dependencies(
        playbook, playbook_path=TEST_PLAYBOOK_PATH
    )

    assert playbooks == ["Get Original Email - Gmail"]
    assert integrations == ["Gmail"]
    assert scripts == ["ReadFile"]
    assert commands == ["gmail-search"]


def test_get_input_data_simple():
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import get_input_data

    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    sample_input = playbook.get("inputs")[1]

    _value = get_input_data(sample_input)

    assert _value == "johnnydepp@gmail.com"


@pytest.mark.parametrize(
    "index, expected_result", [(0, "File.Name"), (2, "No_Accessor")]
)
def test_get_input_data_complex(index, expected_result):
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import get_input_data

    playbook = get_yaml(TEST_PLAYBOOK_PATH)

    sample_input = playbook.get("inputs")[index]

    _value = get_input_data(sample_input)

    assert _value == expected_result


@pytest.mark.parametrize(
    "playbook_name, custom_image_path, expected_result",
    [
        ("playbook name", "", "![playbook name](../doc_files/playbook_name.png)"),
        ("playbook name", "custom_path", "![playbook name](custom_path)"),
    ],
)
def test_generate_image_link(playbook_name, custom_image_path, expected_result):
    """
    Given
    - playbook name
    - custom image path
    - expected result
    When
    - running the generate_image_path command.
    Then
    - Validate that the output of the command matches the expected result.
    """
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import (
        generate_image_path,
    )

    output = generate_image_path(playbook_name, custom_image_path)

    assert output == expected_result


# script tests


def test_get_script_info():
    from demisto_sdk.commands.generate_docs.generate_script_doc import get_script_info

    info = get_script_info(TEST_SCRIPT_PATH)

    assert info[0]["Description"] == "python3"
    assert info[1]["Description"] == "Algosec"
    assert info[2]["Description"] == "5.0.0"


def test_get_script_inputs():
    from demisto_sdk.commands.generate_docs.generate_script_doc import get_inputs

    script = get_yaml(TEST_SCRIPT_PATH)
    inputs, errors = get_inputs(script)

    expected_inputs = [
        {"Argument Name": "InputA", "Description": ""},
        {"Argument Name": "InputB", "Description": "This is input b"},
    ]

    assert inputs == expected_inputs
    assert errors[0] == "Error! You are missing description in script input InputA"


def test_get_script_outputs():
    from demisto_sdk.commands.generate_docs.generate_script_doc import get_outputs

    script = get_yaml(TEST_SCRIPT_PATH)
    outputs, errors = get_outputs(script)

    expected_outputs = [
        {"Path": "outputA", "Description": "This is output a", "Type": "boolean"},
        {"Path": "outputB", "Description": "", "Type": "Unknown"},
    ]

    assert outputs == expected_outputs
    assert errors[0] == "Error! You are missing description in script output outputB"


# integration tests


def test_generate_commands_section():
    yml_data = {
        "script": {
            "commands": [
                {"deprecated": True, "name": "deprecated-cmd"},
                {"deprecated": False, "name": "non-deprecated-cmd"},
            ]
        }
    }

    section, errors = generate_commands_section(
        yml_data, example_dict={}, command_permissions_dict={}
    )

    expected_section = [
        "## Commands",
        "",
        "You can execute these commands from the Cortex XSOAR CLI, as part of an automation, or in a playbook.",
        "After you successfully execute a command, a DBot message appears in the War Room with the command details.",
        "",
        "### non-deprecated-cmd",
        "",
        "***",
        "",
        "#### Required Permissions",
        "",
        "**FILL IN REQUIRED PERMISSIONS HERE**",
        "",
        "#### Base Command",
        "",
        "`non-deprecated-cmd`",
        "",
        "#### Input",
        "",
        "There are no input arguments for this command.",
        "",
        "#### Context Output",
        "",
        "There is no context output for this command.",
    ]

    assert "\n".join(section) == "\n".join(expected_section)


MIRRORING_TEST = [
    (
        {
            "display": "CrowdStrike Falcon",
            "configuration": [
                {"name": "incidents_fetch_query"},
                {"name": "comment_tag", "display": "test comment tag"},
                {"name": "work_notes_tag", "display": "test work notes tag"},
                {
                    "name": "mirror_direction",
                    "options": [
                        "None",
                        "Incoming",
                        "Outgoing",
                        "Incoming And Outgoing",
                    ],
                },
                {"name": "close_incident"},
                {"name": "close_out"},
            ],
        },
        "mirroring_test_markdow",
    ),
    (
        {
            "display": "CrowdStrike Falcon",
            "configuration": [
                {"name": "work_notes_tag", "display": "test work notes tag"},
                {"name": "mirror_direction", "options": ["None", "Incoming"]},
                {"name": "close_incident"},
            ],
        },
        "mirroring_test_markdow_missing",
    ),
]


@pytest.mark.parametrize("yml_content, path_to_result", MIRRORING_TEST)
def test_incident_mirroring_section(yml_content, path_to_result):
    """
    Given
    - An integration that implements incident mirroring.

    When
    - Generating docs for an integration.

    Then
    -  Ensure that the mirroring section being generated as expected.
    """
    test_files_path = Path(
        __file__,
        git_path(),
        "demisto_sdk",
        "commands",
        "generate_docs",
        "tests",
        "test_files",
        path_to_result,
    )
    section = generate_mirroring_section(yml_content)
    with open(test_files_path) as f:
        res = f.read()
    assert "\n".join(section) == res


def test_generate_command_section_with_empty_cotext_example():
    """
    When an string represents an empty dict '{}' is the context output
    the 'Context Example' sections should be empty
    """
    example_dict = {
        "test1": [
            ("!test1", "test without args", "{}"),
            ("!test1 value=val", "test with args", "{}"),
        ]
    }
    command = {"deprecated": False, "name": "test1"}

    section, errors = generate_single_command_section(
        command, example_dict=example_dict, command_permissions_dict={}
    )

    expected_section = [
        "### test1",
        "",
        "***",
        "",
        "#### Required Permissions",
        "",
        "**FILL IN REQUIRED PERMISSIONS HERE**",
        "",
        "#### Base Command",
        "",
        "`test1`",
        "",
        "#### Input",
        "",
        "There are no input arguments for this command.",
        "",
        "#### Context Output",
        "",
        "There is no context output for this command.",
        "#### Command example",
        "```!test1```",
        "#### Human Readable Output",
        "\n>test without args",
        "",
        "#### Command example",
        "```!test1 value=val```",
        "#### Human Readable Output",
        "\n>test with args",
        "",
    ]

    assert "\n".join(section) == "\n".join(expected_section)


def test_generate_command_section_with_empty_cotext_list():
    """
    When given an empty outputs list,
    the 'Context Outputs' sections should indicate they are empty without empty tables.

    Given
    - An empty command context (as an empty list)

    When
    - Running generate_single_command_section

    Then
    -  Ensure that there is no blank table but a proper error that there is no output
    """
    command = {"deprecated": False, "name": "test1", "outputs": []}

    section, errors = generate_single_command_section(
        command, example_dict={}, command_permissions_dict={}
    )

    expected_section = [
        "### test1",
        "",
        "***",
        "",
        "#### Required Permissions",
        "",
        "**FILL IN REQUIRED PERMISSIONS HERE**",
        "",
        "#### Base Command",
        "",
        "`test1`",
        "",
        "#### Input",
        "",
        "There are no input arguments for this command.",
        "",
        "#### Context Output",
        "",
        "There is no context output for this command.",
    ]

    assert "\n".join(section) == "\n".join(expected_section)


def test_generate_commands_section_human_readable():
    yml_data = {
        "script": {
            "commands": [
                {"deprecated": True, "name": "deprecated-cmd"},
                {"deprecated": False, "name": "non-deprecated-cmd"},
            ]
        }
    }

    example_dict = {
        "non-deprecated-cmd": [
            (
                "!non-deprecated-cmd",
                "## this is human readable\nThis is a line\nAnother line",
                "{}",
            ),
        ]
    }

    section, errors = generate_commands_section(
        yml_data, example_dict, command_permissions_dict={}
    )

    hr_section: str = section[section.index("#### Human Readable Output") + 1]
    # get lines except first one which is a \n
    lines = hr_section.splitlines()[1:]
    for line in lines:
        assert line.startswith(">")
    assert lines[0] == ">## this is human readable"
    assert lines[1] == ">This is a line"


def test_generate_commands_with_permissions_section():
    yml_data = {
        "script": {
            "commands": [
                {"deprecated": True, "name": "deprecated-cmd"},
                {"deprecated": False, "name": "non-deprecated-cmd"},
            ]
        }
    }

    section, errors = generate_commands_section(
        yml_data,
        example_dict={},
        command_permissions_dict={"non-deprecated-cmd": "SUPERUSER"},
    )

    expected_section = [
        "## Commands",
        "",
        "You can execute these commands from the Cortex XSOAR CLI, as part of an automation, or in a playbook.",
        "After you successfully execute a command"
        ", a DBot message appears in the War Room with the command details.",
        "",
        "### non-deprecated-cmd",
        "",
        "***",
        "",
        "#### Required Permissions",
        "",
        "SUPERUSER",
        "",
        "#### Base Command",
        "",
        "`non-deprecated-cmd`",
        "",
        "#### Input",
        "",
        "There are no input arguments for this command.",
        "",
        "#### Context Output",
        "",
        "There is no context output for this command.",
    ]

    assert "\n".join(section) == "\n".join(expected_section)


def test_generate_commands_with_permissions_section_command_doesnt_exist():
    """
    Given
        - Integration commands from yml file with command permission flag on.
        - The commands from yml file do not exist in the given command permissions dict.
    When
        - Running the generate_table_section command.
    Then
        - Validate that in the #### Required Permissions section empty string is returned
        - Validate that an error is returned in error list which indicated that for this command no permission were found.
    """
    yml_data = {
        "script": {
            "commands": [
                {"deprecated": True, "name": "deprecated-cmd"},
                {"deprecated": False, "name": "non-deprecated-cmd"},
            ]
        }
    }
    section, errors = generate_commands_section(
        yml_data,
        example_dict={},
        command_permissions_dict={"!non-deprecated-cmd": "SUPERUSER"},
    )

    expected_section = [
        "## Commands",
        "",
        "You can execute these commands from the Cortex XSOAR CLI, as part of an automation, or in a playbook.",
        "After you successfully execute a command, a DBot message appears in the War Room with the command details.",
        "",
        "### non-deprecated-cmd",
        "",
        "***",
        "",
        "#### Required Permissions",
        "",
        "#### Base Command",
        "",
        "`non-deprecated-cmd`",
        "",
        "#### Input",
        "",
        "There are no input arguments for this command.",
        "",
        "#### Context Output",
        "",
        "There is no context output for this command.",
    ]

    assert (
        "Error! Command Permissions were not found for command non-deprecated-cmd"
        in errors
    )
    assert "\n".join(section) == "\n".join(expected_section)


def handle_example(example, insecure):
    parts = example.split()
    name = parts[0].strip("!")
    context = {}
    for p in parts[1:]:
        key, value = p.split("=")
        context[key] = value

    headers = " | ".join(context.keys())
    sep = " | ".join(["---" for _ in range(len(context.keys()))])
    values = " | ".join(context.values())
    human_readable = "\n".join([headers, sep, values])
    return name, human_readable, context, []


def test_generate_playbook_doc_passes_markdownlint(tmp_path):
    """
    Given: A playbook
    When: Generating a readme for the playbook
    Then: The generated readme will have no markdown errors

    """
    generate_playbook_doc(PLAYBOOK_PATH, str(tmp_path), "admin", "a limitation", False)
    with ReadMeValidator.start_mdx_server():
        with open(tmp_path / "beta-playbook-valid_README.md") as file:
            content = file.read()
            markdownlint = run_markdownlint(content)
            assert not markdownlint.has_errors, markdownlint.validations


class TestAppendOrReplaceCommandInDocs:
    positive_test_data_file = os.path.join(
        FILES_PATH, "docs_test", "positive_docs_section_end_with_eof.md"
    )
    command = "dxl-send-event"
    old_doc = open(positive_test_data_file).read()
    new_docs = "\n<NEW DOCS>\n"
    new_command = "\n### dxl-send-event-new-one\n***\nSends the specified event to the DXL fabric.\n##### Base Command\n`dxl-send-event-new-one`"
    new_command += "\n##### Input\n| **Argument Name** | **Description** | **Required** |\n| --- | --- | --- |\n| topic | The topic for which to publish the"
    new_command += " message. | Required |\n| payload | The event payload. | Required |\n##### Context Output\nThere is no context output for this command."
    positive_inputs = [
        (old_doc, new_docs + new_command),
        (
            old_doc + "\n## Known Limitation",
            new_docs + new_command + "\n## Known Limitation",
        ),
        (old_doc + "\n### new-command", new_docs + new_command + "\n### new-command"),
        ("no docs (empty)\n", "no docs (empty)\n" + new_docs),
        (
            f"Command in file, but cant replace. {command}",
            f"Command in file, but cant replace. {command}\n" + new_docs,
        ),
    ]

    @pytest.mark.parametrize("doc_file, output_docs", positive_inputs)
    def test_append_or_replace_command_in_docs_positive(self, doc_file, output_docs):
        docs, _ = append_or_replace_command_in_docs(
            doc_file, self.new_docs, self.command
        )
        assert docs == output_docs


class TestGenerateIntegrationDoc:
    @classmethod
    def rm_readme(cls):
        test_integration_readme = os.path.join(
            os.path.dirname(TEST_INTEGRATION_PATH), "README.md"
        )
        if Path(test_integration_readme).is_file():
            Path(test_integration_readme).unlink()

    @classmethod
    def setup_class(cls):
        cls.rm_readme()

    @classmethod
    def teardown_class(cls):
        cls.rm_readme()

    def test_generate_integration_doc(self, mocker: MockerFixture, tmp_path: Path):
        """
        Given
            - YML file representing an integration.
        When
            - Running generate_integration_doc command on the integration.
        Then
            - Validate that the integration README was created correctly, specifically that line numbers are not being reset after a table.
            - Test that the predefined values and default values are added to the README.
        """
        # TODO add mock for readme/yaml
        import demisto_sdk.commands.generate_docs.common as common

        fake_readme = os.path.join(
            os.path.dirname(TEST_INTEGRATION_PATH), "fake_README.md"
        )
        examples = os.path.join(
            os.path.dirname(TEST_INTEGRATION_PATH), "command_examples.txt"
        )
        mocker.patch.object(common, "execute_command", side_effect=handle_example)
        # Generate doc
        generate_integration_doc(TEST_INTEGRATION_PATH, examples, output=str(tmp_path))
        with open(fake_readme) as fake_file:
            with open(
                os.path.join(str(tmp_path), INTEGRATIONS_README_FILE_NAME)
            ) as real_file:
                fake_data = fake_file.read()
                assert fake_data == real_file.read()

                assert (
                    "The type of the newly created user. Possible values are: Basic, Pro, "
                    "Corporate. Default is Basic." in fake_data
                )
                assert "Number of users to return. Max 300. Default is 30." in fake_data

    def test_generate_integration_doc_new_contribution(
        self, tmp_path: Path, mocker: MockerFixture, git_repo: Repo
    ):
        """
        Given
            - YML file representing a new integration contribution.
        When
            - Running generate_integration_doc command on the integration.
        Then
            - Validate that the integration README was created correctly,
             specifically that the `xx version` line does not exists in the file.
        """

        readme_path = Path(
            Path(TEST_INTEGRATION_PATH).parent, "fake_new_contribution_README.md"
        )
        yml_code_path = Path(TEST_INTEGRATION_PATH)

        git_repo.create_pack("TestPack")
        git_repo.packs[0].create_integration("TestIntegration")

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(tools, "is_external_repository", return_value=True)
        mocker.patch.object(
            TextFile,
            "read_from_git_path",
            side_effect=[yml_code_path.read_text(), readme_path.read_text()],
        )

        # Generate doc
        generate_integration_doc(
            str(yml_code_path), is_contribution=True, output=str(tmp_path)
        )
        with open(readme_path) as fake_file:
            with open(
                os.path.join(str(tmp_path), INTEGRATIONS_README_FILE_NAME)
            ) as real_file:
                fake_data = fake_file.read()
                assert fake_data == real_file.read()
                assert (
                    "This integration was integrated and tested with version xx of"
                    not in fake_data
                )

    def test_generate_integration_doc_contrib_existing_integration(self):
        # TODO add
        pass

    def test_generate_integration_doc_passes_markdownlint(self, tmp_path: Path):
        """
        Given: An integrations
        When: Generating a readme for the integration
        Then: The generated readme will have no markdown errors

        """
        generate_integration_doc(
            TEST_INTEGRATION_PATH, is_contribution=False, output=str(tmp_path)
        )
        # Generate doc
        with ReadMeValidator.start_mdx_server():
            with open(
                os.path.join(str(tmp_path), INTEGRATIONS_README_FILE_NAME)
            ) as real_readme_file:
                markdownlint = run_markdownlint(real_readme_file.read())
                assert not markdownlint.has_errors, markdownlint.validations

    def test_integration_doc_credentials_display_missing(self, tmp_path: Path):
        """
        Given
            - YML file representing an integration, containing display None for credentials parameter.
        When
            - Running generate_integration_doc command on the integration.
        Then
            - Validate that the integration README was created correctly, specifically that line numbers are not being
              reset after a table.
            - Test that the predefined values and default values are added to the README.
            - Test that credentials parameter name shown in README is using display password field.
        """
        readme = os.path.join(
            os.path.dirname(TEST_INTEGRATION_2_PATH), INTEGRATIONS_README_FILE_NAME
        )
        # Generate doc
        generate_integration_doc(
            TEST_INTEGRATION_2_PATH, skip_breaking_changes=True, output=str(tmp_path)
        )
        with open(readme) as readme_file:
            with open(
                os.path.join(
                    os.path.dirname(TEST_INTEGRATION_2_PATH),
                    INTEGRATIONS_README_FILE_NAME,
                )
            ) as new_readme:
                readme_data = readme_file.read()
                assert readme_data == new_readme.read()
                assert (
                    "| None | The API key to use for the connection. | False |"
                    not in readme_data
                )
                assert (
                    "| API Token | The API key to use for the connection. | False |"
                    in readme_data
                )


class TestGetCommandExamples:
    @staticmethod
    def test_examples_with_exclamation_mark(tmp_path):
        """
        Given
            - command_examples file with exclamation mark.
            - list of specific commands.
        When
            - Running get_command_examples with the given command examples and specific commands.
        Then
            - Verify that the returned commands from the examples are only the specific commands.
        """
        command_examples = tmp_path / "command_examples"

        with open(command_examples, "w+") as ce:
            ce.write(
                "!zoom-create-user\n!zoom-create-meeting\n!zoom-fetch-recording\n!zoom-list-users\n!zoom-delete-user"
            )

        command_example_a = "zoom-create-user"
        command_example_b = "zoom-list-users"

        specific_commands = [command_example_a, command_example_b]

        commands = get_command_examples(
            commands_examples_input=command_examples,
            specific_commands=specific_commands,
        )

        assert commands == [f"!{command_example_a}", f"!{command_example_b}"]

    @staticmethod
    def test_examples_without_exclamation_mark(tmp_path):
        """
        Given
            - command_examples file without exclamation mark.
            - list of specific commands.
        When
            - Running get_command_examples with the given command examples and specific commands.
        Then
            - Verify that the returned commands from the examples are only the specific commands.
        """
        command_examples = tmp_path / "command_examples"

        with open(command_examples, "w+") as ce:
            ce.write(
                "zoom-create-user\nzoom-create-meeting\nzoom-fetch-recording\nzoom-list-users\nzoom-delete-user"
            )

        command_example_a = "zoom-create-user"
        command_example_b = "zoom-list-users"

        specific_commands = [command_example_a, command_example_b]

        commands = get_command_examples(
            commands_examples_input=command_examples,
            specific_commands=specific_commands,
        )

        assert commands == [f"!{command_example_a}", f"!{command_example_b}"]

    @staticmethod
    def test_ignored_lines(tmp_path):
        """
        Given
            - command_examples file with comments and empty lines.
        When
            - Running get_command_examples with the given command examples.
        Then
            - Verify that the returned commands from the examples are only the specific commands
        """
        command_examples = tmp_path / "command_examples"

        with open(command_examples, "w+") as ce:
            ce.write(
                "# comment before command\n"
                "zoom-create-user\n"
                "\n"
                "# this is a comment line\n"
                "zoom-create-meeting\n"
            )

        commands = get_command_examples(command_examples, None)

        assert commands == ["!zoom-create-user", "!zoom-create-meeting"]


def test_generate_table_section_numbered_section():
    """
    Given
        - A table that should be part of a numbered section (like the setup section of integration README).
    When
        - Running the generate_table_section command.
    Then
        - Validate that the generated table has \t at the beginning of each line.
    """

    from demisto_sdk.commands.generate_docs.common import generate_table_section

    expected_section = [
        "",
        "    | **Type** | **Docker Image** |",
        "    | --- | --- |",
        "    | python2 | demisto/python2 |",
        "",
    ]

    section = generate_table_section(
        data=[{"Type": "python2", "Docker Image": "demisto/python2"}],
        title="",
        horizontal_rule=False,
        numbered_section=True,
    )
    assert section == expected_section


yml_data_cases = [
    (
        {
            "name": "test",
            "display": "test",
            "configuration": [
                {
                    "defaultvalue": "",
                    "display": "test1",
                    "name": "test1",
                    "required": True,
                    "type": 8,
                },
                {
                    "defaultvalue": "",
                    "display": "test2",
                    "name": "test2",
                    "required": True,
                    "type": 8,
                },
            ],
        },  # case no param with additional info field
        [
            "1. Navigate to **Settings** > **Integrations** > **Servers & Services**.",
            "2. Search for test.",
            "3. Click **Add instance** to create and configure a new integration instance.",
            "",
            "    | **Parameter** | **Required** |",
            "    | --- | --- |",
            "    | test1 | True |",
            "    | test2 | True |",
            "",
            "4. Click **Test** to validate the URLs, token, and connection.",
            "",
        ],  # expected
    ),
    (
        {
            "name": "test",
            "display": "test",
            "configuration": [
                {
                    "display": "test1",
                    "name": "test1",
                    "additionalinfo": "More info",
                    "required": True,
                    "type": 8,
                },
                {"display": "test2", "name": "test2", "required": True, "type": 8},
            ],
        },  # case some params with additional info field
        [
            "1. Navigate to **Settings** > **Integrations** > **Servers & Services**.",
            "2. Search for test.",
            "3. Click **Add instance** to create and configure a new integration instance.",
            "",
            "    | **Parameter** | **Description** | **Required** |",
            "    | --- | --- | --- |",
            "    | test1 | More info | True |",
            "    | test2 |  | True |",
            "",
            "4. Click **Test** to validate the URLs, token, and connection.",
            "",
        ],  # expected
    ),
    (
        {
            "name": "test",
            "display": "test",
            "configuration": [
                {
                    "display": "test1",
                    "name": "test1",
                    "additionalinfo": "More info",
                    "required": True,
                    "type": 8,
                },
                {
                    "display": "test2",
                    "name": "test2",
                    "additionalinfo": "Some more data",
                    "required": True,
                    "type": 8,
                },
            ],
        },  # case all params with additional info field
        [
            "1. Navigate to **Settings** > **Integrations** > **Servers & Services**.",
            "2. Search for test.",
            "3. Click **Add instance** to create and configure a new integration instance.",
            "",
            "    | **Parameter** | **Description** | **Required** |",
            "    | --- | --- | --- |",
            "    | test1 | More info | True |",
            "    | test2 | Some more data | True |",
            "",
            "4. Click **Test** to validate the URLs, token, and connection.",
            "",
        ],  # expected
    ),
    (
        {
            "name": "test",
            "display": "test",
            "configuration": [
                {
                    "display": "userName",
                    "displaypassword": "password",
                    "name": "userName",
                    "additionalinfo": "Credentials",
                    "required": True,
                    "type": 9,
                },
            ],
        },  # case credentials parameter have displaypassword
        [
            "1. Navigate to **Settings** > **Integrations** > **Servers & Services**.",
            "2. Search for test.",
            "3. Click **Add instance** to create and configure a new integration instance.",
            "",
            "    | **Parameter** | **Description** | **Required** |",
            "    | --- | --- | --- |",
            "    | userName | Credentials | True |",
            "    | password |  | True |",
            "",
            "4. Click **Test** to validate the URLs, token, and connection.",
            "",
        ],  # expected
    ),
    (
        {
            "name": "test",
            "display": "test",
            "configuration": [
                {
                    "display": "userName",
                    "name": "userName",
                    "additionalinfo": "Credentials",
                    "required": True,
                    "type": 9,
                },
            ],
        },  # case credentials parameter have no displaypassword
        [
            "1. Navigate to **Settings** > **Integrations** > **Servers & Services**.",
            "2. Search for test.",
            "3. Click **Add instance** to create and configure a new integration instance.",
            "",
            "    | **Parameter** | **Description** | **Required** |",
            "    | --- | --- | --- |",
            "    | userName | Credentials | True |",
            "    | Password |  | True |",
            "",
            "4. Click **Test** to validate the URLs, token, and connection.",
            "",
        ],  # expected
    ),
    (
        {
            "name": "test",
            "display": "test",
            "configuration": [
                {
                    "display": "test1",
                    "name": "test1",
                    "additionalinfo": "More info",
                    "required": True,
                    "type": 8,
                },
                {
                    "display": "API key",
                    "name": "API key",
                    "additionalinfo": "",
                    "required": True,
                    "type": 8,
                },
                {
                    "display": "Proxy",
                    "name": "Proxy",
                    "additionalinfo": "non-default info.",
                    "required": True,
                    "type": 8,
                },
            ],
        },  # case some param with additional information, one that should take default, and one overriding default
        [
            "1. Navigate to **Settings** > **Integrations** > **Servers & Services**.",
            "2. Search for test.",
            "3. Click **Add instance** to create and configure a new integration instance.",
            "",
            "    | **Parameter** | **Description** | **Required** |",
            "    | --- | --- | --- |",
            "    | test1 | More info | True |",
            "    | API key | The API Key to use for the connection. | True |",
            "    | Proxy | non-default info. | True |",
            "",
            "4. Click **Test** to validate the URLs, token, and connection.",
            "",
        ],  # expected
    ),
]


@pytest.mark.parametrize("yml_input, expected_results", yml_data_cases)
def test_generate_setup_section_with_additional_info(yml_input, expected_results):
    """
    Given
        - A yml file with parameters in configuration section
    When
        - Running the generate_setup_section command.
    Then
        - Validate that the generated table has the 'Description' column if
        at least one parameter has the additionalinfo field.
    """
    section = generate_setup_section(yml_input)
    assert section == expected_results


def test_scripts_in_playbook(repo):
    """
    Given
        - A test playbook file
    When
        - Run get_playbook_dependencies command
    Then
        - Ensure that the scripts we get are from both the script and scriptName fields.
    """
    from demisto_sdk.commands.generate_docs.generate_playbook_doc import (
        get_playbook_dependencies,
    )

    pack = repo.create_pack("pack")
    playbook = pack.create_playbook("LargePlaybook")
    test_task_1 = {
        "id": "1",
        "ignoreworker": False,
        "isautoswitchedtoquietmode": False,
        "isoversize": False,
        "nexttasks": {"#none#": ["2"]},
        "note": False,
        "quietmode": 0,
        "separatecontext": True,
        "skipunavailable": False,
        "task": {
            "brand": "",
            "id": "dcf48154-7e80-42b3-8464-7156e1cd3d10",
            "iscommand": False,
            "name": "test_script",
            "scriptName": "test_1",
            "type": "regular",
            "version": -1,
        },
        "scriptarguments": {
            "encoding": {},
            "entryID": {"simple": "entryId"},
            "maxFileSize": {},
        },
        "taskid": "dcf48154-7e80-42b3-8464-7156e1cd3d10",
        "timertriggers": [],
        "type": "playbook",
    }
    test_task_2 = {
        "id": "2",
        "ignoreworker": False,
        "isautoswitchedtoquietmode": False,
        "isoversize": False,
        "nexttasks": {"#none#": ["3"]},
        "note": False,
        "quietmode": 0,
        "separatecontext": True,
        "skipunavailable": False,
        "task": {
            "brand": "",
            "id": "dcf48154-7e80-42b3-8464-7156e1cd3d10",
            "iscommand": False,
            "name": "test_script",
            "script": "test_2",
            "type": "regular",
            "version": -1,
        },
        "scriptarguments": {
            "encoding": {},
            "entryID": {"simple": "entryId"},
            "maxFileSize": {},
        },
        "taskid": "dcf48154-7e80-42b3-8464-7156e1cd3d10",
        "timertriggers": [],
        "type": "playbook",
    }
    playbook.create_default_playbook()
    playbook_data = playbook.yml.read_dict()
    playbook_data["tasks"]["1"] = test_task_1
    playbook_data["tasks"]["2"] = test_task_2
    playbook.yml.write_dict(playbook_data)

    playbooks, integrations, scripts, commands = get_playbook_dependencies(
        playbook_data, playbook_path=playbook.yml.rel_path
    )

    assert "test_1" in scripts
    assert "test_2" in scripts


TEST_ADD_ACCESS_DATA_OF_TYPE_CREDENTIALS_INPUTS: List[
    Tuple[List, Dict[str, Any], List[Dict[str, Any]]]
] = [
    (
        [],
        {"display": "username", "additionalinfo": "Username", "required": True},
        [
            {"Parameter": "username", "Description": "Username", "Required": True},
            {"Description": "", "Parameter": "Password", "Required": True},
        ],
    ),
    (
        [],
        {
            "displaypassword": "specialPassword",
            "additionalinfo": "Enter your password",
            "required": False,
        },
        [
            {
                "Description": "Enter your password",
                "Parameter": "specialPassword",
                "Required": False,
            }
        ],
    ),
    (
        [],
        {
            "display": "username",
            "additionalinfo": "Username",
            "required": True,
            "displaypassword": "specialPassword",
        },
        [
            {"Parameter": "username", "Description": "Username", "Required": True},
            {"Description": "", "Parameter": "specialPassword", "Required": True},
        ],
    ),
]


@pytest.mark.parametrize(
    "access_data, credentials_conf, expected",
    TEST_ADD_ACCESS_DATA_OF_TYPE_CREDENTIALS_INPUTS,
)
def test_add_access_data_of_type_credentials(
    access_data: List[Dict], credentials_conf: Dict, expected: List[Dict]
):
    """
    Given:
    - 'access_data': Containing parameter data to be added to README file.
    - 'credentials_conf': Credentials configuration data represented as a dict.

    When:
    - Adding to README the parameter credential conf configuration details.
    Case a: Only display name exists, display password does not.
    Case b: Only display password name exists, display not.
    Case c: Both display name and display password name exists.

    Then:
    - Ensure the expected credentials data is added to 'access_data'.
    Case a: Display name is added, also 'Password' is added as default for display password name missing.
    Case b: 'Password' is added as default for display password name missing.
    Case c: Both display name and display password name are added.
    """
    from demisto_sdk.commands.generate_docs.generate_integration_doc import (
        add_access_data_of_type_credentials,
    )

    add_access_data_of_type_credentials(access_data, credentials_conf)
    assert access_data == expected


def test_generate_versions_differences_section(monkeypatch):
    """
    Given
        - A new version of an integration.
    When
        - Running the generate_versions_differences_section command.
    Then
        - Add a section of differences between versions in README.
    """

    from demisto_sdk.commands.generate_docs.generate_integration_doc import (
        generate_versions_differences_section,
    )

    monkeypatch.setattr("builtins.input", lambda _: "")
    section = generate_versions_differences_section("", "", "Integration_Display_Name")

    expected_section = [
        "## Breaking changes from the previous version of this integration - Integration_Display_Name",
        "%%FILL HERE%%",
        "The following sections list the changes in this version.",
        "",
        "### Commands",
        "#### The following commands were removed in this version:",
        "* *commandName* - this command was replaced by XXX.",
        "* *commandName* - this command was replaced by XXX.",
        "",
        "### Arguments",
        "#### The following arguments were removed in this version:",
        "",
        "In the *commandName* command:",
        "* *argumentName* - this argument was replaced by XXX.",
        "* *argumentName* - this argument was replaced by XXX.",
        "",
        "#### The behavior of the following arguments was changed:",
        "",
        "In the *commandName* command:",
        "* *argumentName* - is now required.",
        "* *argumentName* - supports now comma separated values.",
        "",
        "### Outputs",
        "#### The following outputs were removed in this version:",
        "",
        "In the *commandName* command:",
        "* *outputPath* - this output was replaced by XXX.",
        "* *outputPath* - this output was replaced by XXX.",
        "",
        "In the *commandName* command:",
        "* *outputPath* - this output was replaced by XXX.",
        "* *outputPath* - this output was replaced by XXX.",
        "",
        "## Additional Considerations for this version",
        "%%FILL HERE%%",
        "* Insert any API changes, any behavioral changes, limitations, or "
        "restrictions that would be new to this version.",
        "",
    ]

    assert section == expected_section


def test_disable_md_autolinks():
    """
    Given
        - Markdown with http link.
    When
        - Run disable_md_autolinks.
    Then
        - Make sure non-md links are escaped. MD links should remain in place.
    """
    assert disable_md_autolinks("http://test.com") == "http:<span>//</span>test.com"
    no_replace_str = "(link)[http://test.com]"
    assert disable_md_autolinks(no_replace_str) == no_replace_str
    no_replace_str = "nohttp://test.com"
    assert disable_md_autolinks(no_replace_str) == no_replace_str
    # taken from here: https://github.com/demisto/content/pull/13423/files
    big_str = """{'language': 'python', 'status': 'success', 'status-message': '11 fixed alerts', 'new': 0, 'fixed': 11, 'alerts': [{'query': {'id': 9980089, 'pack': 'com.lgtm/python-queries', 'name': 'Statement has no effect', 'language': 'python', 'properties': {'id': 'py/ineffectual-statement', 'name': 'Statement has no effect', 'severity': 'recommendation', 'tags': ['maintainability', 'useless-code', 'external/cwe/cwe-561']}, 'url': 'https://lgtm.com/rules/9980089'}, 'new': 0, 'fixed': 0}, {'query': {'id': 1510006386081, 'pack': 'com.lgtm/python-queries', 'name': 'Clear-text storage of sensitive information', 'language': 'python', 'properties': {'id': 'py/clear-text-storage-sensitive-data', 'name': 'Clear-text storage of sensitive information', 'severity': 'error', 'tags': ['security', 'external/cwe/cwe-312', 'external/cwe/cwe-315', 'external/cwe/cwe-359']}, 'url': 'https://lgtm.com/rules/1510006386081'}, 'new': 0, 'fixed': 1}, {'query': {'id': 6780086, 'pack': 'com.lgtm/python-queries', 'name': 'Unused local variable', 'language': 'python', 'properties': {'id': 'py/unused-local-variable', 'name': 'Unused local variable', 'severity': 'recommendation', 'tags': ['maintainability', 'useless-code', 'external/cwe/cwe-563']}, 'url': 'https://lgtm.com/rules/6780086'}, 'new': 0, 'fixed': 4}, {'query': {'id': 1800095, 'pack': 'com.lgtm/python-queries', 'name': 'Variable defined multiple times', 'language': 'python', 'properties': {'id': 'py/multiple-definition', 'name': 'Variable defined multiple times', 'severity': 'warning', 'tags': ['maintainability', 'useless-code', 'external/cwe/cwe-563']}, 'url': 'https://lgtm.com/rules/1800095'}, 'new': 0, 'fixed': 4}, {'query': {'id': 3960089, 'pack': 'com.lgtm/python-queries', 'name': 'Explicit returns mixed with implicit (fall through) returns', 'language': 'python', 'properties': {'id': 'py/mixed-returns', 'name': 'Explicit returns mixed with implicit (fall through) returns', 'severity': 'recommendation', 'tags': ['reliability', 'maintainability']}, 'url': 'https://lgtm.com/rules/3960089'}, 'new': 0, 'fixed': 0}, {'query': {'id': 1780094, 'pack': 'com.lgtm/python-queries', 'name': 'Wrong number of arguments in a call', 'language': 'python', 'properties': {'id': 'py/call/wrong-arguments', 'name': 'Wrong number of arguments in a call', 'severity': 'error', 'tags': ['reliability', 'correctness', 'external/cwe/cwe-685']}, 'url': 'https://lgtm.com/rules/1780094'}, 'new': 0, 'fixed': 2}, {'query': {'id': 10030095, 'pack': 'com.lgtm/python-queries', 'name': 'File is not always closed', 'language': 'python', 'properties': {'id': 'py/file-not-closed', 'name': 'File is not always closed', 'severity': 'warning', 'tags': ['efficiency', 'correctness', 'resources', 'external/cwe/cwe-772']}, 'url': 'https://lgtm.com/rules/10030095'}, 'new': 0, 'fixed': 0}]} | https://lgtm.com/projects/g/my-devsecops/moon/rev/pr- """
    res = disable_md_autolinks(big_str)
    assert "http://" not in res
    assert res.count("https:<span>//</span>") == 8


TEST_EMPTY_SCRIPTDATA_SECTION = [
    ({"script": "some info"}, [""]),
    (
        {"subtype": "python2", "tags": []},
        [
            "## Script data",
            "",
            "---",
            "",
            "| **Name** | **Description** |",
            "| --- | --- |",
            "| Script Type | python2 |",
            "",
        ],
    ),
    ({"tags": []}, [""]),
    (
        {"fromversion": "0.0.0"},
        [
            "## Script data",
            "",
            "---",
            "",
            "| **Name** | **Description** |",
            "| --- | --- |",
            "| Cortex XSOAR Version | 0.0.0 |",
            "",
        ],
    ),
]


@pytest.mark.parametrize("yml_content, expected_result", TEST_EMPTY_SCRIPTDATA_SECTION)
def test_missing_data_sections_when_generating_table_section(
    yml_content, expected_result, pack: Pack
):
    """Unit test
    Given
    - Case 1: yml with no relevant tags for 'get_script_info' function.
    - Case 2: yml with 'subtype' section filled in and empty 'tags' section.
    - Case 3: yml that contain empty 'tags' section.
    - Case 4: yml that contain 'fromversion' section that is different from 'DEFAULT_CONTENT_ITEM_FROM_VERSION_FOR_RN' (which is 6.0.0).
    When
    - running the get_script_info command on the inputs and then generate_table_section.
    Then
    - Validate That the generated table section was created correctly.
    - Case 1: Empty table section.
    - Case 2: Script data section with a title and a table containing information only about the script type.
    - Case 3: Empty table section.
    - Case 4: Script data section with a title and a table containing information only about the Cortex XSOAR Version.
    """
    from demisto_sdk.commands.generate_docs.common import generate_table_section
    from demisto_sdk.commands.generate_docs.generate_script_doc import get_script_info

    script_pack = pack.create_script()
    script_pack.yml.write_dict(yml_content)

    script_info = get_script_info(script_pack.yml.path, clear_cache=True)
    section = generate_table_section(script_info, "Script data")
    assert section == expected_result


class TestIntegrationDocUpdate:

    repo_dir_name = "content"
    pack_name = integration_name = "AHA"

    def _get_function_name(self) -> str:
        return inspect.currentframe().f_back.f_code.co_name  # type:ignore

    def test_added_commands(self, mocker: MockerFixture, git_repo: Repo):
        """
        Check that newly-added commands to the integration YAML
        are appended to the integration README.

        Given:
        - A Pack with an integration

        When:
        - The original integration has 4 commands.
        - The modified integration has 5 commands.

        Then:
        - The difference is 1 command.
        """

        # Initialize Integration YAML, README.
        yml_code_path = Path(
            TEST_FILES, self._get_function_name(), f"{self.integration_name}.yml"
        )
        modified_yml_path = Path(
            TEST_FILES,
            self._get_function_name(),
            f"{self.integration_name}_added_cmd.yml",
        )
        with yml_code_path.open("r") as stream:
            yml_code = yaml.load(stream)

        readme_path = Path(
            TEST_FILES, self._get_function_name(), INTEGRATIONS_README_FILE_NAME
        )

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(tools, "is_external_repository", return_value=True)
        mocker.patch.object(
            TextFile,
            "read_from_git_path",
            side_effect=[yml_code_path.read_text(), readme_path.read_text()],
        )

        # Create Pack and Integration
        git_repo.create_pack(self.pack_name)
        git_repo.packs[0].create_integration(
            self.integration_name, yml=yml_code, readme=readme_path.read_text()
        )

        shutil.copyfile(
            src=modified_yml_path, dst=git_repo.packs[0].integrations[0].yml.path
        )

        generate_integration_doc(input_path=git_repo.packs[0].integrations[0].yml.path)

        actual = git_repo.packs[0].integrations[0].readme.read()

        assert "aha-delete-idea" in actual

    def test_identical_integration_yaml(self, mocker: MockerFixture, git_repo: Repo):
        """
        Test where the integration YAMLs are identical.

        Given:
        - A content repo with an integration (YAML + README).
        - An integration YAML.

        When:
        - The supplied integration YAML is identical to the one in the repo.

        Then:
        - The generated README is unchaged/identical to the one in the repo.
        """

        yml_code_path = Path(
            TEST_FILES, "test_added_commands", f"{self.integration_name}.yml"
        )
        with yml_code_path.open("r") as stream:
            yml_code = yaml.load(stream)

        readme_path = Path(
            TEST_FILES, "test_added_commands", INTEGRATIONS_README_FILE_NAME
        )

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(tools, "is_external_repository", return_value=True)
        mocker.patch.object(
            TextFile,
            "read_from_git_path",
            side_effect=[yml_code_path.read_text(), readme_path.read_text()],
        )

        # Create Pack and Integration
        git_repo.create_pack(self.pack_name)
        git_repo.packs[0].create_integration(
            self.integration_name, yml=yml_code, readme=readme_path.read_text()
        )

        generate_integration_doc(input_path=str(yml_code_path))

        actual = git_repo.packs[0].integrations[0].readme.read()
        expected = readme_path.read_text()

        assert actual == expected

    def test_added_configuration(self, mocker: MockerFixture, git_repo: Repo):
        """
        Test to check a scenario where an integration configuration is added.

        Given:
        - A content repo with an integration

        When:
        - A new integration configuration was added.

        Then:
        - The integration configuration section should have the
        new option added.
        """

        # Initialize Integration YAML, README.

        yml_code_path = Path(
            TEST_FILES, self._get_function_name(), f"{self.integration_name}.yml"
        )
        modified_yml_path = Path(
            TEST_FILES,
            self._get_function_name(),
            f"{self.integration_name}_added_conf.yml",
        )
        with yml_code_path.open("r") as stream:
            yml_code = yaml.load(stream)

        readme_path = Path(
            TEST_FILES, self._get_function_name(), INTEGRATIONS_README_FILE_NAME
        )

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(tools, "is_external_repository", return_value=True)
        mocker.patch.object(
            TextFile,
            "read_from_git_path",
            side_effect=[yml_code_path.read_text(), readme_path.read_text()],
        )

        # Create Pack and Integration
        git_repo.create_pack(self.pack_name)
        git_repo.packs[0].create_integration(
            self.integration_name, yml=yml_code, readme=readme_path.read_text()
        )

        shutil.copyfile(
            src=modified_yml_path, dst=git_repo.packs[0].integrations[0].yml.path
        )

        generate_integration_doc(input_path=git_repo.packs[0].integrations[0].yml.path)

        actual = git_repo.packs[0].integrations[0].readme.read()

        assert "Project ID" in actual

    def test_update_commands_section(self, mocker: MockerFixture, git_repo: Repo):
        """
        Test to check an integration commands section update.

        Given:
        - A new integration YAML.
        - An old integration YAML.

        When:
        - The integration commands have the following changes:
            - The `defaultValue` field was removed from `from_date` argument in the `aha-get-features` command.
            - The `defaultValue` field was changed (30 -> 50) from `per_page` argument in the`aha-get-features` command.
            - The `assigned_to_user` argument was added to the `aha-get-features` command.
            - The `description` field was changed in the `aha-edit-idea` command.
            - The `workflow_status` argument was added to the `aha-edit-idea` command.
            - The `AHA.Idea.updated_at` context path was added to the `output` of the `aha-edit-idea` command.

        Then:
        - 2 errors are returned for missing command examples.
        - The new configuration option is present in the README.
        """

        yml_code_path = Path(
            TEST_FILES, self._get_function_name(), f"{self.integration_name}.yml"
        )
        modified_yml_path = Path(
            TEST_FILES,
            self._get_function_name(),
            f"{self.integration_name}_modified_cmds.yml",
        )
        with yml_code_path.open("r") as stream:
            yml_code = yaml.load(stream)

        readme_path = Path(
            TEST_FILES, self._get_function_name(), INTEGRATIONS_README_FILE_NAME
        )

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(tools, "is_external_repository", return_value=True)
        mocker.patch.object(
            TextFile,
            "read_from_git_path",
            side_effect=[yml_code_path.read_text(), readme_path.read_text()],
        )

        # Create Pack and Integration
        git_repo.create_pack(self.pack_name)
        git_repo.packs[0].create_integration(
            self.integration_name, yml=yml_code, readme=readme_path.read_text()
        )

        shutil.copyfile(
            src=modified_yml_path, dst=git_repo.packs[0].integrations[0].yml.path
        )

        generate_integration_doc(input_path=git_repo.packs[0].integrations[0].yml.path)

        actual = git_repo.packs[0].integrations[0].readme.read()

        assert (
            "| from_date | Show features created after this date. | Optional |"
            in actual
        )
        assert (
            "| per_page | The maximum number of results per page. Default is 50."
            in actual
        )
        assert (
            "| assigned_to_user | The user the feature is assigned to. | Optional |"
            in actual
        )
        assert (
            "| workflow_status | The status to change the idea to. Default is Shipped. | Optional |"
            in actual
        )
        assert "| AHA.Idea.updated_at | Date | The idea update date. |" in actual
        assert "#### Required Permissions" not in actual

    def test_added_conf_cmd_modified_cmd(self, git_repo: Repo, mocker: MockerFixture):
        """
        Test for a scenario where we:
        - Add a new configuration option.
        - Add a new command.
        - Modify a command argument and output.

        Given:
        - A repo with a SplunkPy integration

        When:
        - A new configuration option was added.
        - A new command was added.
        - A command argument and output were modified.

        Then:
        - The configuration should be added to the setup section of the README.
        - The added command should be appended to the README.
        - The modified argument and output should be reflected in the README.
        """

        pack_name = integration_name = "SplunkPy"

        yml_code_path = Path(
            TEST_FILES, self._get_function_name(), f"{integration_name}.yml"
        )
        modified_yml_path = Path(
            TEST_FILES, self._get_function_name(), f"{integration_name}_update.yml"
        )
        with yml_code_path.open("r") as stream:
            yml_code = yaml.load(stream)

        readme_path = Path(
            TEST_FILES, self._get_function_name(), INTEGRATIONS_README_FILE_NAME
        )

        # Create Pack and Integration
        git_repo.create_pack(pack_name)
        git_repo.packs[0].create_integration(
            integration_name, yml=yml_code, readme=readme_path.read_text()
        )

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(tools, "is_external_repository", return_value=True)
        mocker.patch.object(
            TextFile,
            "read_from_git_path",
            side_effect=[yml_code_path.read_text(), readme_path.read_text()],
        )

        shutil.copyfile(
            src=modified_yml_path, dst=git_repo.packs[0].integrations[0].yml.path
        )

        generate_integration_doc(input_path=git_repo.packs[0].integrations[0].yml.path)

        actual = git_repo.packs[0].integrations[0].readme.read().splitlines()
        actual[61] == "    | Debug logging enabled |  | False |"
        actual[
            804
        ] == "| limit | Maximum number of records to return. Default is 100. | Optional |"
        actual[805] == "| new_arg | New argument for testing. | Optional | "
        actual[812] == "| Splunk.Test | String | Test output for Splunk | "
        assert actual[1149:1171] == [
            "### splunk-test-cmd",
            "",
            "***",
            "A new test command",
            "",
            "#### Base Command",
            "",
            "`splunk-test-cmd`",
            "",
            "#### Input",
            "",
            "| **Argument Name** | **Description** | **Required** |",
            "| --- | --- | --- |",
            "| some_arg | Test argument for new command. | Required | ",
            "",
            "#### Context Output",
            "",
            "| **Path** | **Type** | **Description** |",
            "| --- | --- | --- |",
            "| Splunk.Test.Output | String | Some sample test output | ",
            "| Splunk.Test.Date | Date | Some sample test output date | ",
            "",
        ]

    def test_added_conf_cmd_modified_cmd_with_examples(
        self, git_repo: Repo, mocker: MockerFixture
    ):
        """
        Test for a scenario where we:
        - Add a new configuration option.
        - Add a new command.
        - Modify a command argument and output.

        Given:
        - A content repo with an existing integration.

        When:
        - A new configuration option was added.
        - A new command was added.
        - A command argument and output were modified.
        - Command examples are provided.

        Then:
        - The configuration should be added to the setup section of the README.
        - The added command should be appended to the README.
        - The modified argument and output should be reflected in the README.
        - Command examples should be added to each command section.
        """

        pack_name = integration_name = "Test"
        existing_integration_yml = {
            "description": "Test integration",
            "name": integration_name,
            "display": integration_name,
            "category": "Analytics & SIEM",
            "script": {
                "commands": [
                    {
                        "name": f"{integration_name.lower()}-get-log",
                        "description": "Gets log",
                        "arguments": [
                            {
                                "name": "log_name",
                                "description": "The log name to retrieve",
                                "required": False,
                                "defaultValue": "all",
                            },
                            {
                                "name": "log_ts",
                                "description": "The log timestamp to retrieve",
                                "required": False,
                            },
                        ],
                        "outputs": [
                            {
                                "contextPath": "Test.Log.name",
                                "description": "The log name",
                                "type": "String",
                            },
                            {
                                "contextPath": "Test.Log.id",
                                "description": "The log ID.",
                                "type": "String",
                            },
                        ],
                    },
                    {
                        "name": f"{integration_name.lower()}-get-alert",
                        "description": "Gets alert",
                        "arguments": [
                            {
                                "name": "alert_name",
                                "description": "The alert name to retrieve",
                                "required": False,
                                "defaultValue": "all",
                            },
                            {
                                "name": "alert_ts",
                                "description": "The alert timestamp to retrieve",
                                "required": False,
                            },
                            {
                                "name": "alert_max",
                                "description": "The maximum amount of alerts to retrieve",
                                "required": False,
                                "defaultValue": 100,
                            },
                        ],
                    },
                ]
            },
            "configuration": [
                {
                    "display": "Base URL",
                    "name": "base_url",
                    "required": True,
                    "type": 0,
                },
                {"display": "Port", "name": "port", "required": True, "type": 0},
            ],
            "commonfields": {"id": integration_name, "version": -1},
            "fromversion": "6.0.0",
        }

        existing_readme = [f"# Integration Documentation for {integration_name}"]
        existing_readme.extend(generate_setup_section(existing_integration_yml))
        commands_section, _ = generate_commands_section(
            existing_integration_yml, example_dict={}, command_permissions_dict={}
        )
        existing_readme.extend(commands_section)

        updated_integration_yml = {
            "description": "Test integration",
            "name": integration_name,
            "category": "Analytics & SIEM",
            "display": integration_name,
            "script": {
                "commands": [
                    {
                        "name": f"{integration_name.lower()}-get-log",
                        "description": "Gets log",
                        "arguments": [
                            {
                                "name": "log_name",
                                "description": "The log name to retrieve",
                                "required": False,
                                "defaultValue": "all",
                            },
                            {
                                "name": "log_ts",
                                "description": "The log timestamp to retrieve",
                                "required": False,
                            },
                            {
                                "name": "alert_max",
                                "description": "The maximum amount of alerts to retrieve",
                                "required": False,
                                "defaultValue": 100,
                            },
                        ],
                        "outputs": [
                            {
                                "contextPath": "Test.Log.name",
                                "description": "The log name",
                                "type": "String",
                            },
                            {
                                "contextPath": "Test.Log.id",
                                "description": "The log ID.",
                                "type": "String",
                            },
                        ],
                    },
                    {
                        "name": f"{integration_name.lower()}-get-alert",
                        "description": "Gets alert",
                        "arguments": [
                            {
                                "name": "alert_name",
                                "description": "The alert name to retrieve",
                                "required": False,
                            },
                            {
                                "name": "alert_ts",
                                "description": "The alert timestamp to retrieve",
                                "required": False,
                            },
                            {
                                "name": "alert_max",
                                "description": "The maximum amount of alerts to retrieve",
                                "required": False,
                                "defaultValue": 100,
                            },
                        ],
                    },
                    {
                        "name": f"{integration_name.lower()}-get-audits",
                        "description": "Gets audits",
                        "arguments": [
                            {
                                "name": "audit_name",
                                "description": "The audit name to retrieve",
                                "required": False,
                            },
                            {
                                "name": "audit_ts",
                                "description": "The audit timestamp to retrieve",
                                "required": False,
                            },
                            {
                                "name": "audit_max",
                                "description": "The maximum amount of audits to retrieve",
                                "required": False,
                                "defaultValue": 100,
                            },
                        ],
                    },
                ]
            },
            "configuration": [
                {
                    "display": "Base URL",
                    "name": "base_url",
                    "required": True,
                    "type": 0,
                },
                {
                    "display": "Port",
                    "name": "port",
                    "required": False,
                    "defaultValue": "443",
                    "type": 0,
                },
                {
                    "display": "Authentication",
                    "name": "authentication",
                    "required": True,
                    "type": 9,
                },
            ],
            "commonfields": {"id": integration_name, "version": -1},
            "fromversion": "6.0.0",
        }

        # commands = f"!{integration_name}-get-log\n!{integration_name}-get-alert\n"
        commands = f"!{integration_name.lower()}-get-log"

        # Create Pack and Integration
        git_repo.create_pack(pack_name)
        git_repo.packs[0].create_integration(
            integration_name,
            yml=existing_integration_yml,
            readme="\n".join(existing_readme),
            commands_txt=commands,
        )

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(tools, "is_external_repository", return_value=True)
        mocker.patch.object(
            TextFile,
            "read_from_git_path",
            side_effect=[
                yaml.dumps(existing_integration_yml),
                "\n".join(existing_readme),
            ],
        )
        mocker.patch.object(
            common,
            "execute_command",
            return_value=(
                f"{integration_name.lower()}-get-log",
                """#### Command example
```test-get-log```

#### Context Example
```json
{
    "name": "foo",
    "id": 1
}
```""",
                {"Test.Log.name": "foo", "Test.Log.id": 1},
                [],
            ),
        )

        # Update the integration
        git_repo.packs[0].integrations[0].yml.write_dict(updated_integration_yml)

        generate_integration_doc(
            input_path=git_repo.packs[0].integrations[0].yml.path,
            examples=os.path.join(
                git_repo.packs[0].integrations[0].path, "commands.txt"
            ),
        )

        actual_readme = Path(
            os.path.join(
                git_repo.path,
                "Packs",
                integration_name,
                "Integrations",
                integration_name,
                INTEGRATIONS_README_FILE_NAME,
            )
        ).read_text()

        assert "Password | True" not in "\n".join(existing_readme)
        assert "#### Command example" not in "\n".join(existing_readme)
        assert "#### Context Example" not in "\n".join(existing_readme)
        assert f"{integration_name.lower()}-get-audits" not in "\n".join(
            existing_readme
        )

        assert "Password | True" in actual_readme
        assert "#### Command example" in actual_readme
        assert "#### Context Example" in actual_readme
        assert f"{integration_name.lower()}-get-audits" in actual_readme
