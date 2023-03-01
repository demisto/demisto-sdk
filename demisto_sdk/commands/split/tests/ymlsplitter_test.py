import base64
import os
from pathlib import Path
from unittest.mock import mock_open

from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import DEFAULT_IMAGE_BASE64
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)
from demisto_sdk.commands.prepare_content.tests.yml_unifier_test import (
    DUMMY_MODULE,
    DUMMY_SCRIPT,
)
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter
from TestSuite.test_tools import ChangeCWD

yaml = YAML_Handler()
json = JSON_Handler()


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
    os.remove(extractor.output)


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
    os.remove(output)


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
    os.remove(output)


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
    os.remove(output)


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
    os.remove(output)


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


def test_extract_code(tmpdir):
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml",
        output=str(tmpdir.join("temp_code.py")),
        file_type="integration",
    )

    extractor.extract_code(extractor.output)
    with open(extractor.output, "rb") as temp_code:
        file_data = temp_code.read().decode("utf-8")
        assert "import demistomock as demisto  #" in file_data
        assert "from CommonServerPython import *  #" in file_data
        assert file_data[-1] == "\n"
        assert "register_module_line" not in file_data
    os.remove(extractor.output)

    extractor.common_server = False
    extractor.demisto_mock = False
    extractor.extract_code(extractor.output)
    with open(extractor.output, "rb") as temp_code:
        file_data = temp_code.read().decode("utf-8")
        assert "import demistomock as demisto  #" not in file_data
        assert "from CommonServerPython import *  #" not in file_data
        assert "register_module_line" not in file_data
        assert file_data[-1] == "\n"


def test_extract_code__with_apimodule(tmpdir):
    """
    Given:
        - A unified YML which ApiModule code is auto-generated there
    When:
        - run YmlSpltter on this code
    Then:
        - Ensure generated code is being deleted, and the import line exists
    """
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-EDL.yml",
        output=str(tmpdir.join("temp_code.py")),
        file_type="integration",
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


def test_extract_code_pwsh(tmpdir):
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-powershell_ssh_remote.yml",
        output=str(tmpdir.join("temp_code")),
        file_type="integration",
    )

    extractor.extract_code(extractor.output)
    # notice that we passed without an extension. Extractor should be adding .ps1
    with open(extractor.output.with_suffix(".ps1"), encoding="utf-8") as temp_code:
        file_data = temp_code.read()
        assert ". $PSScriptRoot\\CommonServerPowerShell.ps1\n" in file_data
        assert file_data[-1] == "\n"


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


def test_extract_to_package_format_pwsh(tmpdir):
    out = tmpdir.join("Integrations")
    extractor = YmlSplitter(
        input=f"{git_path()}/demisto_sdk/tests/test_files/integration-powershell_ssh_remote.yml",
        output=str(out),
        file_type="integration",
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
        DUMMY_SCRIPT, {import_name: module_name}
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
