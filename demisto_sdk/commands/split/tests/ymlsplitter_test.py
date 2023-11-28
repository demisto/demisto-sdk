import base64
from pathlib import Path
from unittest.mock import mock_open

import pytest

from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import DEFAULT_IMAGE_BASE64
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)
from demisto_sdk.commands.prepare_content.tests.yml_unifier_test import (
    DUMMY_MODULE,
    DUMMY_SCRIPT,
)
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter
from TestSuite.test_tools import ChangeCWD


def test_extract_long_description(tmpdir):
    # Test when script
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/script-test_script.yml",
        output="",
        file_type="script",
        no_demisto_mock=False,
        no_common_server=False,
        configuration=Configuration(),
    )
    assert extractor.extract_long_description("output_path") == 0

    # Test opening the file and writing to it
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml",
        output=str(tmpdir.join("temp_text.txt")),
        file_type="integration",
    )

    extractor.extract_long_description(extractor.output)
    with open(extractor.output, "rb") as temp_description:
        assert temp_description.read().decode("utf-8") == "detaileddescription"
    Path(extractor.output).unlink()


def test_extract_modeling_rules(tmpdir):
    """
    Given:
        - A unified YML of a Modeling Rule
    When:
        - run extract_rules
    Then:
        - Ensure that the rules were extracted
    """
    output = str(tmpdir.join("temp_rules.xif"))
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/modelingrule-OktaModelingRules.yml",
        file_type="modelingrule",
    )

    extractor.extract_rules(output)
    with open(output, "rb") as temp_rules:
        temp_rules = temp_rules.read()
        assert "[MODEL: dataset=okta_okta_raw, model=Audit]" in str(temp_rules)
    Path(output).unlink()


def test_extract_modeling_rules_schema(tmpdir):
    """
    Given:
        - A unified YML of a Modeling Rule
    When:
        - run extract_rule_schema
    Then:
        - Ensure that the schema was extracted
    """
    schema = {
        "okta_okta_raw": {
            "client": {"type": "string", "is_array": False},
            "eventType": {"type": "string", "is_array": False},
        }
    }
    output = str(tmpdir.join("temp_rules.json"))
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/modelingrule-OktaModelingRules.yml",
        file_type="modelingrule",
    )

    extractor.extract_rule_schema_and_samples(output)
    with open(output, "rb") as temp_rules:
        temp_rules = temp_rules.read()
        assert schema == json.loads(temp_rules)
    Path(output).unlink()


def test_extract_parsing_rules(tmpdir):
    """
    Given:
        - A unified YML of a Parsing Rule
    When:
        - run extract_rules
    Then:
        - Ensure that the rules were extracted
    """
    output = str(tmpdir.join("temp_rules.xif"))
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/parsingrule-MyParsingRules.yml",
        file_type="parsingrule",
    )

    extractor.extract_rules(output)
    with open(output, "rb") as temp_rules:
        temp_rules = temp_rules.read()
        assert "[RULE:extract_hipmatch_only_fields]" in str(temp_rules)
    Path(output).unlink()


def test_extract_parsing_rules_sampels(tmpdir):
    """
    Given:
        - A unified YML of a Parsing Rule
    When:
        - run extract_rule_schema
    Then:
        - Ensure that the sample was extracted
    """
    sample = {
        "okta_on_prem": [
            {
                "cefVersion": "CEF:0",
                "cefDeviceVendor": "Zscaler",
                "cefDeviceProduct": "NSSWeblog",
            }
        ]
    }
    output = str(tmpdir.join("temp_rules.json"))
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/parsingrule-MyParsingRules.yml",
        file_type="parsingrule",
    )

    extractor.extract_rule_schema_and_samples(output)
    with open(output, "rb") as temp_rules:
        temp_rules = temp_rules.read()
        assert sample == json.loads(temp_rules)
    Path(output).unlink()


def test_extract_to_package_format_modeling_rule(tmpdir):
    """
    Given:
        - A unified YML of a Modeling Rule
    When:
        - run extract_to_package_format
    Then:
        - Ensure that all files has been created successfully
    """
    out = tmpdir.join("ModelingRules")
    schema = {
        "okta_okta_raw": {
            "client": {"type": "string", "is_array": False},
            "eventType": {"type": "string", "is_array": False},
        }
    }
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/modelingrule-OktaModelingRules.yml",
        output=str(out),
        file_type="modelingrule",
    )
    assert extractor.extract_to_package_format() == 0
    # check code
    with open(
        out.join("OktaModelingRule").join("OktaModelingRule.xif"), encoding="utf-8"
    ) as f:
        file_data = f.read()
        assert "[MODEL: dataset=okta_okta_raw, model=Audit]" in file_data

    with open(
        out.join("OktaModelingRule").join("OktaModelingRule_schema.json"),
        encoding="utf-8",
    ) as f:
        file_data = f.read()
        assert schema == json.loads(file_data)

    with open(out.join("OktaModelingRule").join("OktaModelingRule.yml")) as f:
        yaml_obj = yaml.load(f)
        assert yaml_obj["fromversion"] == "6.8.0"


def test_extract_to_package_format_parsing_rule(tmpdir):
    """
    Given:
        - A unified YML of a Parsing Rule
    When:
        - run extract_to_package_format
    Then:
        - Ensure that all files has been created successfully
    """
    out = tmpdir.join("ModelingRules")
    sample = {
        "okta_on_prem": [
            {
                "cefVersion": "CEF:0",
                "cefDeviceVendor": "Zscaler",
                "cefDeviceProduct": "NSSWeblog",
            }
        ]
    }
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/parsingrule-MyParsingRules.yml",
        output=str(out),
        file_type="parsingrule",
    )
    assert extractor.extract_to_package_format() == 0
    # check code
    with open(out.join("MyRule").join("MyRule.xif"), encoding="utf-8") as f:
        file_data = f.read()
        assert "[RULE:extract_hipmatch_only_fields]" in file_data

    with open(out.join("MyRule").join("MyRule.json"), encoding="utf-8") as f:
        file_data = f.read()
        assert sample == json.loads(file_data)

    with open(out.join("MyRule").join("MyRule.yml")) as f:
        yaml_obj = yaml.load(f)
        assert yaml_obj["fromversion"] == "6.8.0"


def test_extract_image(tmpdir):
    # Test when script
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/script-test_script.yml",
        output="",
        file_type="script",
    )
    assert extractor.extract_image("output_path") == 0

    # Test opening the file and writing to it
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml",
        output=str(tmpdir.join("temp_image.png")),
        file_type="integration",
    )

    extractor.extract_image(extractor.output)
    with open(extractor.output, "rb") as temp_image:
        image_data = temp_image.read()
        image = base64.b64encode(image_data).decode("utf-8")
        assert image == DEFAULT_IMAGE_BASE64


@pytest.mark.parametrize(
    argnames="file_path,file_type",
    argvalues=[
        (
            f"{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml",
            "integration",
        ),
        (
            f"{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml",
            "betaintegration",
        ),
        (
            f"{git_path()}/demisto_sdk/tests/test_files/integration-Zoom-no-trailing-newline.yml",
            "integration",
        ),
    ],
)
def test_extract_code(tmpdir, file_path, file_type):
    """
    Given
        Case 1: a unified integration file of python format.
        Case 2: a unified beta-integration file of python format.
        Case 3: a unified integration file of python format without a trailing newline in the script.

    When
    - Running the YmlSplitter extract_code function.

    Then
    - Ensure that all lines that should have been removed have been removed.
    """
    extractor = YmlSplitter(
        input=file_path,
        output=str(tmpdir.join("temp_code.py")),
        file_type=file_type,
    )
    script_before_split = yaml.load(Path(extractor.input).read_text())["script"][
        "script"
    ]
    assert "### pack version: 1.0.3" in script_before_split
    assert "# pack version: 1.0.3" in script_before_split
    assert "#### pack version: 1.0.3" in script_before_split

    extractor.extract_code(extractor.output)
    with open(extractor.output, "rb") as temp_code:
        file_data = temp_code.read().decode("utf-8")
        assert "import demistomock as demisto  #" in file_data
        assert "from CommonServerPython import *  #" in file_data
        assert file_data[-1] == "\n"
        assert "register_module_line" not in file_data
        assert "### pack version: 1.0.3" not in file_data
        assert "# pack version: 1.0.3" not in file_data
        assert "#### pack version: 1.0.3" not in file_data
    Path(extractor.output).unlink()

    extractor.common_server = False
    extractor.demisto_mock = False
    extractor.extract_code(extractor.output)
    with open(extractor.output, "rb") as temp_code:
        file_data = temp_code.read().decode("utf-8")
        assert "import demistomock as demisto  #" not in file_data
        assert "from CommonServerPython import *  #" not in file_data
        assert "register_module_line" not in file_data
        assert "### pack version: 1.0.3" not in file_data
        assert "# pack version: 1.0.3" not in file_data
        assert "#### pack version: 1.0.3" not in file_data
        assert file_data[-1] == "\n"


@pytest.mark.parametrize(
    argnames="file_type", argvalues=[("integration"), ("betaintegration")]
)
def test_extract_javascript_code(tmpdir, file_type):
    """
    Given
    Case 1: a unified integration file of javascript format.
    Case 2: a unified beta-integration file of javascript format.

    When
    - Running the YmlSplitter extract_code function.

    Then
    - Ensure the "// pack version: ..." comment was removed successfully.
    """
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-Zoom-js.yml",
        output=str(tmpdir.join("temp_code.js")),
        file_type=file_type,
    )
    assert (
        "// pack version: 1.0.3"
        in yaml.load(Path(extractor.input).read_text())["script"]["script"]
    )

    extractor.extract_code(extractor.output)
    file_data = Path(extractor.output).read_text()
    assert "// pack version: 1.0.3" not in file_data
    Path(extractor.output).unlink()


@pytest.mark.parametrize(
    argnames="file_type", argvalues=[("integration"), ("betaintegration")]
)
def test_extract_powershell_code(tmpdir, file_type):
    """
    Given
        Case 1: a unified integration file of powershell format.
        Case 2: a unified beta-integration file of powershell format.
    When
    - Running the YmlSplitter extract_code function.
    Then
    - Ensure the "### pack version: ..." comment was removed successfully.
    """
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-Zoom-ps1.yml",
        output=str(tmpdir.join("temp_code.ps1")),
        file_type=file_type,
    )
    assert (
        "### pack version: 1.0.3"
        in yaml.load(Path(extractor.input).read_text())["script"]["script"]
    )

    extractor.extract_code(extractor.output)
    with open(extractor.output, "rb") as temp_code:
        file_data = temp_code.read().decode("utf-8")
        assert "### pack version: 1.0.3" not in file_data
    Path(extractor.output).unlink()


@pytest.mark.parametrize(
    argnames="file_type", argvalues=[("integration"), ("betaintegration")]
)
def test_extract_code__with_apimodule(tmpdir, file_type):
    """
    Given:
        Case 1: A unified integration YML which ApiModule code is auto-generated there
        Case 2: A unified beta-integration YML which ApiModule code is auto-generated there
    When:
        - Run YmlSplitter on this code
    Then:
        - Ensure generated code is being deleted, and the import line exists
    """
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-EDL.yml",
        output=str(tmpdir.join("temp_code.py")),
        file_type=file_type,
    )

    extractor.extract_code(extractor.output)
    with open(extractor.output, "rb") as temp_code:
        file_data = temp_code.read().decode("utf-8")
        assert "### GENERATED CODE ###" not in file_data
        assert "### END GENERATED CODE ###" not in file_data
        assert "from NGINXApiModule import *" in file_data
        assert (
            "def create_nginx_server_conf(file_path: str, port: int, params: Dict):"
            not in file_data
        )


def test_extract_code_modules_old_format(tmpdir):
    """
    Given:
        - A unified YML which ApiModule code is auto-generated there, but the comments are not up to date
    When:
        - run YmlSpltter on this code
    Then:
        - Make sure that the imported code is still there, and the code runs.
    """
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-EDL_old_generated.yml",
        output=str(tmpdir.join("temp_code.py")),
        file_type="integration",
    )

    extractor.extract_code(extractor.output)
    with open(extractor.output, "rb") as temp_code:
        file_data = temp_code.read().decode("utf-8")
        assert "### GENERATED CODE ###" in file_data
        assert "def nginx_log_process(nginx_process: subprocess.Popen):" in file_data


@pytest.mark.parametrize(
    argnames="file_type", argvalues=[("integration"), ("betaintegration")]
)
def test_extract_code_pwsh(tmpdir, file_type):
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-powershell_ssh_remote.yml",
        output=str(tmpdir.join("temp_code")),
        file_type=file_type,
    )

    extractor.extract_code(extractor.output)
    # notice that we passed without an extension. Extractor should be adding .ps1
    with open(extractor.output.with_suffix(".ps1"), encoding="utf-8") as temp_code:
        file_data = temp_code.read()
        assert ". $PSScriptRoot\\CommonServerPowerShell.ps1\n" in file_data
        assert file_data[-1] == "\n"


def test_extraction_with_period_in_filename(pack):
    """
    Given: A unified YAML file with a filename containing a period (that might be identified as an extension)
    When: Running YmlSplitter on this file
    Then: Files are extracted with the appropriate filenames
    """
    integration = pack.create_integration(
        name="Zoom-v1.0",
        description="Test",
        create_unified=True,
    )

    YmlSplitter(
        input=integration.yml.path,
        output=str(Path(pack.path) / "Integrations"),
        base_name="Zoom-v1.0",
        file_type="integration",
    ).extract_to_package_format()

    expected_integration_dir = Path(pack.path) / "Integrations" / "ZoomV10"
    assert expected_integration_dir.exists()

    extracted_files = [str(file.name) for file in expected_integration_dir.glob("*")]
    assert len(extracted_files) == 5

    assert {
        "README.md",
        "Zoom-v1.0_description.md",
        "Zoom-v1.0_image.png",
        "Zoom-v1.0.py",
        "Zoom-v1.0.yml",
    } == set(extracted_files)


def test_get_output_path():
    out = f"{git_path()}/demisto_sdk/tests/Integrations"
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml",
        file_type="integration",
        output=out,
    )
    res = extractor.get_output_path()
    assert res == Path(out + "/Zoom")


def test_get_output_path_relative(repo):
    pack = repo.create_pack()
    integration = pack.create_integration()

    with ChangeCWD(repo.path):
        extractor = YmlSplitter(input=integration.yml.rel_path, file_type="integration")

    output_path = extractor.get_output_path()
    assert output_path.is_absolute()
    assert output_path.relative_to(pack.path) == Path(integration.path).relative_to(
        pack.path
    )


def test_get_output_path_empty_output():
    input_path = Path(f"{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml")
    extractor = YmlSplitter(input=str(input_path), file_type="integration")
    res = extractor.get_output_path()
    assert res == input_path.parent


@pytest.mark.parametrize(
    argnames="file_type", argvalues=[("integration"), ("betaintegration")]
)
def test_extract_to_package_format_pwsh(tmpdir, file_type):
    out = tmpdir.join("Integrations")
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-powershell_ssh_remote.yml",
        output=str(out),
        file_type=file_type,
    )
    assert extractor.extract_to_package_format() == 0
    # check code
    with open(
        out.join("PowerShellRemotingOverSSH").join("PowerShellRemotingOverSSH.ps1"),
        encoding="utf-8",
    ) as f:
        file_data = f.read()
        assert ". $PSScriptRoot\\CommonServerPowerShell.ps1\n" in file_data
        assert file_data[-1] == "\n"
    # check description
    with open(
        out.join("PowerShellRemotingOverSSH").join(
            "PowerShellRemotingOverSSH_description.md"
        )
    ) as f:
        file_data = f.read()
        assert (
            "Username and password are both associated with the user in the target machine"
            in file_data
        )
    # check readme
    with open(out.join("PowerShellRemotingOverSSH").join("README.md")) as f:
        file_data = f.read()
        assert "This is a sample test README" in file_data
    with open(
        out.join("PowerShellRemotingOverSSH").join("PowerShellRemotingOverSSH.yml")
    ) as f:
        yaml_obj = yaml.load(f)
        assert yaml_obj["fromversion"] == "5.5.0"
        assert not yaml_obj["script"]["script"]


def get_dummy_module(name="MicrosoftApiModule", path=None):
    class_name = {
        "MicrosoftApiModule": "MicrosoftClient",
        "CrowdStrikeApiModule": "CrowdStrikeApiClient",
    }[name]
    return DUMMY_MODULE.replace("CLASSNAME", class_name)


def test_update_api_module_contribution(mocker):
    m = mock_open()
    mock = mocker.patch("demisto_sdk.commands.split.ymlsplitter.open", m)
    mocker.patch.object(
        IntegrationScriptUnifier,
        "_get_api_module_code",
        return_value=get_dummy_module(),
    )
    import_name = "from MicrosoftApiModule import *  # noqa: E402"
    module_name = "MicrosoftApiModule"
    code = IntegrationScriptUnifier.insert_module_code(
        DUMMY_SCRIPT, {import_name: module_name}, Path()
    )
    yml_splitter = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/modelingrule-OktaModelingRules.yml",
        file_type="modelingrule",
    )
    yml_splitter.replace_imported_code(code, executed_from_contrib_converter=True)
    write_calls = mock().write.call_args_list
    assert (
        f"{write_calls[0].args[0]}{write_calls[1].args[0]}\n{write_calls[2].args[0]}\n"
        == f"from CommonServerPython import *  # noqa: F401\n"
        f"import demistomock as demisto  # noqa: F401\n"
        f"{get_dummy_module()}"
    )


def test_input_file_data_parameter(mocker, monkeypatch):
    """
    Given: A unified YML file
    When: Using YmlSplitter on this file with the 'input_file_data' parameter, which allows passing pre-loaded data,
        to avoid unnecessary loading from disk.
    Then: Ensure that the data is used instead of loading from disk.
    """
    import demisto_sdk.commands.common.tools

    input_path = Path(f"{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml")
    file_data = get_yaml(file_path=input_path)

    get_yaml_mock = mocker.spy(demisto_sdk.commands.common.tools, "get_yaml")
    monkeypatch.setattr(
        "demisto_sdk.commands.split.ymlsplitter.get_yaml", get_yaml_mock
    )
    extractor = YmlSplitter(
        input=str(input_path), input_file_data=file_data, file_type="integration"
    )
    assert get_yaml_mock.call_count == 0

    # Assure "get_yaml" is called when not using 'input_file_data', and that the loaded data is the same as the
    # preloaded data.
    extractor = YmlSplitter(input=str(input_path), file_type="integration")
    assert get_yaml_mock.call_count == 1
    assert extractor.yml_data == file_data
