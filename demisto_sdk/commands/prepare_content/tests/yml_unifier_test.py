import base64
import copy
import logging
import os
import re
import shutil
from pathlib import Path

import pytest
import requests
from click.testing import CliRunner

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.constants import (
    GOOGLE_CLOUD_STORAGE_PUBLIC_BASE_PATH,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)
from demisto_sdk.commands.prepare_content.prepare_upload_manager import (
    PrepareUploadManager,
)
from TestSuite.test_tools import ChangeCWD, str_in_call_args_list

TEST_VALID_CODE = """import demistomock as demisto
from CommonServerPython import *

def main():
    return_error('Not implemented.')
\u200b
if __name__ in ('builtins', '__builtin__', '__main__'):
    main()
"""

TEST_VALID_DETAILED_DESCRIPTION = """first line
second line

## header1
do the following:
1. say hello
2. say goodbye
"""

DUMMY_SCRIPT = '''
def main():
""" COMMANDS MANAGER / SWITCH PANEL """
    command = demisto.command()
    args = demisto.args()
    LOG(f'Command being called is {command}')

    params = demisto.params()


try:
    if command == 'test-module':
        demisto.results('ok')
except Exception as e:
    return_error(str(e))


from MicrosoftApiModule import *  # noqa: E402
from CrowdStrikeApiModule import *

if __name__ in ["builtins", "__main__"]:
    main()
'''

DUMMY_MODULE = """
import requests
import base64
from typing import Dict, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

OPROXY_AUTH_TYPE = 'oproxy'
SELF_DEPLOYED_AUTH_TYPE = 'self_deployed'


class CLASSNAME(BaseClient):

    def __init__(self, tenant_id: str = '', auth_id: str = '', enc_key: str = '',
                 token_retrieval_url: str = '', app_name: str = '', refresh_token: str = '',
                 client_id: str = '', client_secret: str = '', scope: str = '', resource: str = '', app_url: str = '',
                 verify: bool = True, auth_type: str = OPROXY_AUTH_TYPE, *args, **kwargs):

"""

TESTS_DIR = f"{git_path()}/demisto_sdk/tests"


def get_dummy_module(name="MicrosoftApiModule", path=None):
    class_name = {
        "MicrosoftApiModule": "MicrosoftClient",
        "CrowdStrikeApiModule": "CrowdStrikeApiClient",
    }[name]
    return DUMMY_MODULE.replace("CLASSNAME", class_name)


def test_clean_python_code():
    script_code = (
        "import demistomock as demisto\nfrom CommonServerPython import *  # test comment being removed\n"
        "from CommonServerUserPython import *\nfrom __future__ import print_function"
    )
    # Test remove_print_future is False
    script_code = IntegrationScriptUnifier.clean_python_code(
        script_code, remove_print_future=False
    )
    assert script_code == "\n\n\nfrom __future__ import print_function"
    # Test remove_print_future is True
    script_code = IntegrationScriptUnifier.clean_python_code(script_code)
    assert script_code.strip() == ""


def test_get_code_file():
    # Test integration case
    package_path = f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/"
    assert (
        IntegrationScriptUnifier.get_code_file(package_path, ".py")
        == f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB.py"
    )
    with pytest.raises(Exception):
        IntegrationScriptUnifier.get_code_file(
            f"{git_path()}/demisto_sdk/tests/test_files/Unifier/SampleNoPyFile", ".py"
        )
    # Test script case
    assert (
        IntegrationScriptUnifier.get_code_file(
            f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/", ".py"
        )
        == f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/CalculateGeoDistance.py"
    )


def test_get_code_file_case_insensative(tmp_path):
    # Create an integration dir with some files
    integration_dir = tmp_path / "TestDummyInt"
    os.makedirs(integration_dir)
    open(integration_dir / "Dummy.ps1", "a")
    open(
        integration_dir / "ADummy.tests.ps1", "a"
    )  # a test file which is named such a way that it comes up first
    assert IntegrationScriptUnifier.get_code_file(integration_dir, ".ps1") == str(
        integration_dir / "Dummy.ps1"
    )


def test_get_script_or_integration_package_data():
    with pytest.raises(Exception):
        IntegrationScriptUnifier.get_script_or_integration_package_data(
            f"{git_path()}/demisto_sdk/tests/test_files/Unifier/SampleNoPyFile"
        )
    with open(
        f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/CalculateGeoDistance.py"
    ) as code_file:
        code = code_file.read()
    (
        yml_path,
        code_data,
    ) = IntegrationScriptUnifier.get_script_or_integration_package_data(
        Path(f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance")
    )
    assert (
        yml_path
        == f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/CalculateGeoDistance.yml"
    )
    assert code_data == code


def test_get_data():
    package_path = Path(f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/")
    with open(
        f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_image.png", "rb"
    ) as image_file:
        image = image_file.read()
    data, found_data_path = IntegrationScriptUnifier.get_data(
        package_path, "*png", False
    )
    assert data == image
    assert (
        found_data_path
        == f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_image.png"
    )
    data, found_data_path = IntegrationScriptUnifier.get_data(
        package_path, "*png", True
    )
    assert data is None
    assert found_data_path is None


def test_insert_description_to_yml():
    package_path = Path(f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/")
    with open(
        f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_description.md", "rb"
    ) as desc_file:
        desc_data = desc_file.read().decode("utf-8")
    integration_doc_link = (
        "\n\n---\n[View Integration Documentation]"
        "(https://xsoar.pan.dev/docs/reference/integrations/vuln-db)"
    )
    yml_unified, found_data_path = IntegrationScriptUnifier.insert_description_to_yml(
        package_path, {"commonfields": {"id": "VulnDB"}}, False
    )

    assert (
        found_data_path
        == f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_description.md"
    )
    assert (desc_data + integration_doc_link) == yml_unified["detaileddescription"]


@pytest.fixture
def description_as_bytes():
    return b"""
This is a desc with an image url link
![image](https://raw.githubusercontent.com/demisto/content/master/Images/campaign-overview.png)
"""


@pytest.mark.parametrize("is_script, res", [(False, True), (True, False)])
def test_insert_description_to_yml_with_markdown_image(
    is_script, res, mocker, description_as_bytes
):
    """
    Given:
        - an integration path a unified yml and a marketplace
        - a script path ..
    When:
        - Parsing and preparing the description file
    Then
        - Validate that the pack folder (test_files) and that the GCS are in the description path.
        - Validate that the description did not change by the markdown_image_handler.
    """
    mocker.patch.object(
        IntegrationScriptUnifier, "get_data", return_value=(description_as_bytes, True)
    )
    package_path = Path("Packs/CybleEventsV2/Integrations/CybleEventsV2")
    yml_unified, _ = IntegrationScriptUnifier.insert_description_to_yml(
        package_path,
        {"commonfields": {"id": "VulnDB"}},
        is_script,
        MarketplaceVersions.XSOAR,
    )
    assert (
        GOOGLE_CLOUD_STORAGE_PUBLIC_BASE_PATH in yml_unified["detaileddescription"]
    ) == res
    assert ("CybleEventsV2" in yml_unified["detaileddescription"]) == res


def test_insert_description_to_yml_with_no_detailed_desc(tmp_path):
    """
    Given:
        - Integration with empty detailed description and with non-empty README

    When:
        - Inserting detailed description to the unified integration YAML

    Then:
        - Verify the integration doc markdown link is inserted to the detailed description
    """
    readme = tmp_path / "README.md"
    readme.write_text("README")
    detailed_desc = tmp_path / "integration_description.md"
    detailed_desc.write_text("")
    yml_unified, _ = IntegrationScriptUnifier.insert_description_to_yml(
        tmp_path, {"commonfields": {"id": "some integration id"}}, False
    )
    assert (
        "[View Integration Documentation](https://xsoar.pan.dev/docs/reference/integrations/some-integration-id)"
        == yml_unified["detaileddescription"]
    )


def test_get_integration_doc_link_positive(tmp_path):
    """
    Given:
        - Cortex XDR - IOC integration with README

    When:
        - Getting integration doc link

    Then:
        - Verify the expected integration doc markdown link is returned
        - Verify the integration doc URL exists and reachable
    """
    readme = tmp_path / "README.md"
    readme.write_text("README")
    integration_doc_link = IntegrationScriptUnifier.get_integration_doc_link(
        tmp_path, {"commonfields": {"id": "Cortex XDR - IOC"}}
    )
    assert (
        integration_doc_link
        == "[View Integration Documentation](https://xsoar.pan.dev/docs/reference/integrations/cortex-xdr---ioc)"
    )
    link = re.findall(r"\(([^)]+)\)", integration_doc_link)[0]
    try:
        r = requests.get(link, verify=False, timeout=10)
        r.raise_for_status()
    except requests.HTTPError as ex:
        raise Exception(f"Failed reaching to integration doc link {link} - {ex}")


def test_get_integration_doc_link_negative(tmp_path):
    """
    Given:
        - Case A: integration which does not have README in the integration dir
        - Case B: integration with empty README in the integration dir
    When:
        - Getting integration doc link
    Then:
        - Verify an empty string is returned
    """
    integration_doc_link = IntegrationScriptUnifier.get_integration_doc_link(
        tmp_path, {"commonfields": {"id": "Integration With No README"}}
    )
    assert integration_doc_link == ""

    readme = tmp_path / "README.md"
    readme.write_text("")
    integration_doc_link = IntegrationScriptUnifier.get_integration_doc_link(
        tmp_path, {"commonfields": {"id": "Integration With Empty README"}}
    )
    assert integration_doc_link == ""


def test_insert_description_to_yml_doc_link_exist(tmp_path, mocker):
    """
    Given:
        - integration which have a detailed description with "View Integration Documentation" doc link

    When:
        - Getting integration doc link

    Then:
        - Verify get_integration_doc_link function is not called
    """
    detailed_desc = tmp_path / "integration_description.md"
    detailed_desc.write_text(
        "[View Integration Documentation]"
        "(https://xsoar.pan.dev/docs/reference/integrations/some-integration-id)"
    )
    mock_func = mocker.patch.object(
        IntegrationScriptUnifier, "get_integration_doc_link", return_result=""
    )
    yml_unified, _ = IntegrationScriptUnifier.insert_description_to_yml(
        tmp_path, {"commonfields": {"id": "some integration id"}}, False
    )
    assert mock_func.call_count == 0


def test_insert_image_to_yml():
    package_path = Path(f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/")
    image_prefix = "data:image/png;base64,"
    with open(
        f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_image.png", "rb"
    ) as image_file:
        image_data = image_file.read()
        image_data = image_prefix + base64.b64encode(image_data).decode("utf-8")
    with open(
        f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB.yml", encoding="utf-8"
    ) as yml_file:
        yml_unified_test = yaml.load(yml_file)
    yml_unified, found_img_path = IntegrationScriptUnifier.insert_image_to_yml(
        package_path, yml_unified_test, False, image_prefix
    )
    yml_unified_test["image"] = image_data
    assert (
        found_img_path
        == f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_image.png"
    )
    assert yml_unified == yml_unified_test


def test_insert_image_to_yml_without_image(tmp_path):
    """
    Given:
     - Integration without image png file

    When:
     - Inserting image to unified YAML

    Then:
     - Ensure the insertion does not crash
     - Verify no image path is returned
    """
    integration_dir = tmp_path / "Integrations"
    integration_dir.mkdir()
    integration_yml = integration_dir / "SomeIntegration.yml"
    integration_obj = {"id": "SomeIntegration"}
    yaml.dump(integration_obj, integration_yml.open("w"))
    yml_unified, found_img_path = IntegrationScriptUnifier.insert_image_to_yml(
        integration_dir, integration_obj, False
    )
    assert yml_unified == integration_obj
    assert not found_img_path


def test_check_api_module_imports():
    """
    Given:
     - A dummy script with 2 import statements

    When:
     - calling check_api_module_imports

    Then:
     - Recieve a dict of import to name
    """
    import_to_name = IntegrationScriptUnifier.check_api_module_imports(DUMMY_SCRIPT)
    assert import_to_name == {
        "from MicrosoftApiModule import *  # noqa: E402": "MicrosoftApiModule",
        "from CrowdStrikeApiModule import *": "CrowdStrikeApiModule",
    }


@pytest.mark.parametrize(
    "import_to_module",
    [
        {
            "from MicrosoftApiModule import *  # noqa: E402": "MicrosoftApiModule",
            "from CrowdStrikeApiModule import *": "CrowdStrikeApiModule",
        },
        {"from MicrosoftApiModule import *": "MicrosoftApiModule"},
    ],
)
def test_insert_module_code(mocker, import_to_module):
    """
    Given:
     - Import statements and its respective module name

    When:
     - calling get_generated_module_code

    Then:
     - Ensure the code returned contains the mocked module code
    """
    mocker.patch.object(
        IntegrationScriptUnifier, "_get_api_module_code", side_effect=get_dummy_module
    )
    expected_result = DUMMY_SCRIPT
    for import_name, module_name in import_to_module.items():
        module_code = get_generated_module_code(import_name, module_name)

        expected_result = expected_result.replace(import_name, module_code)
        assert module_code in expected_result

    code = IntegrationScriptUnifier.insert_module_code(
        DUMMY_SCRIPT, import_to_module, Path()
    )

    assert code == expected_result


def test_insert_hierarchy_api_module(mocker):
    """
    Given:
     - An ApiModule which imports another ApiModule

    When:
     - calling insert_module_code

    Then:
     - Ensure the code returned contains both inner and outer api modules
    """

    def mocked_get_api_module_code(*args, **kwargs):
        if args[0] == "SubApiModule":
            return "from MicrosoftApiModule import *"
        return get_dummy_module()

    import_to_name = {"from SubApiModule import *": "SubApiModule"}
    mocker.patch.object(
        IntegrationScriptUnifier,
        "_get_api_module_code",
        side_effect=mocked_get_api_module_code,
    )

    code = IntegrationScriptUnifier.insert_module_code(
        "from SubApiModule import *", import_to_name, Path()
    )
    assert (
        "register_module_line('MicrosoftApiModule', 'start', __line__(), wrapper=-3)\n"
        in code
    )
    assert (
        "register_module_line('SubApiModule', 'start', __line__(), wrapper=-3)\n"
        in code
    )


def test_insert_pack_version_and_script_to_yml():
    """
    Given:
     - A pack name.

    When:
     - calling insert_pack_version.

    Then:
     - Ensure the code returned contains the pack version in it.
    """
    version_str = "### pack version: 1.0.3"
    assert version_str not in DUMMY_SCRIPT
    assert version_str in IntegrationScriptUnifier.insert_pack_version(
        ".py", DUMMY_SCRIPT, "1.0.3"
    )
    assert version_str in IntegrationScriptUnifier.insert_pack_version(
        ".ps1", DUMMY_SCRIPT, "1.0.3"
    )
    assert version_str not in IntegrationScriptUnifier.insert_pack_version(
        ".js", DUMMY_SCRIPT, "1.0.3"
    )
    version_str_js = "// pack version: 1.0.3"
    assert version_str_js not in DUMMY_SCRIPT
    assert version_str_js in IntegrationScriptUnifier.insert_pack_version(
        ".js", DUMMY_SCRIPT, "1.0.3"
    )


def get_generated_module_code(import_name, api_module_name):
    return (
        f"\n### GENERATED CODE ###"
        f": {import_name}\n"
        f"# This code was inserted in place of an API module.\n"
        f"register_module_line('{api_module_name}', 'start', __line__(), wrapper=-3)\n"
        f"{get_dummy_module(api_module_name)}\n"
        f"register_module_line('{api_module_name}', 'end', __line__(), wrapper=1)\n"
        f"### END GENERATED CODE ###"
    )


def test_insert_module_code__verify_offsets(mocker):
    """
    When:
        replacing ApiModule code
    Given:
        a script with an ApiModule import
    Then:
        verify the wrapper of the section line numbers are correct.
    """
    mocker.patch.object(
        IntegrationScriptUnifier,
        "_get_api_module_code",
        return_value=get_dummy_module(),
    )
    import_name = "from MicrosoftApiModule import *  # noqa: E402"
    before_api_import, after_api_import = DUMMY_SCRIPT.split(import_name, 1)
    module_name = "MicrosoftApiModule"

    code = IntegrationScriptUnifier.insert_module_code(
        DUMMY_SCRIPT, {import_name: module_name}, Path()
    )
    # get only the generated ApiModule code
    code = code[len(before_api_import) : -len(after_api_import)]

    # we expect the start wrapper will have a negative number so adding it to the regex search
    start_offset = re.search(
        rf"register_module_line\('{module_name}', 'start', __line__\(\), wrapper=-(\d+)\)\n",
        code,
    )
    end_offset = re.search(
        rf"register_module_line\('{module_name}', 'end', __line__\(\), wrapper=(\d+)\)\n",
        code,
    )

    assert start_offset
    # the number of lines before the register start match the wrapper value
    assert int(start_offset.group(1)) == len(
        code[: start_offset.span()[0]].splitlines()
    )
    assert end_offset
    # the number of lines after the register end match the wrapper value
    assert int(end_offset.group(1)) == len(code[end_offset.span()[1] :].splitlines())


@pytest.mark.parametrize(
    "package_path, dir_name, file_path",
    [
        (
            f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/",
            "Integrations",
            f"{git_path()}/demisto_sdk/tests/test_files/" f"VulnDB/VulnDB",
        ),
        (
            f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/",
            "Scripts",
            f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/CalculateGeoDistance",
        ),
    ],
)
def test_insert_script_to_yml(package_path, dir_name, file_path):
    is_script_package = dir_name == "Scripts"
    with open(file_path + ".yml") as yml:
        test_yml_data = yaml.load(yml)

    test_yml_unified = copy.deepcopy(test_yml_data)

    yml_unified, script_path = IntegrationScriptUnifier.insert_script_to_yml(
        Path(package_path), ".py", test_yml_unified, test_yml_data, is_script_package
    )

    with open(file_path + ".py", encoding="utf-8") as script_file:
        script_code = script_file.read()
    clean_code = IntegrationScriptUnifier.clean_python_code(script_code)

    if isinstance(test_yml_unified.get("script", {}), str):
        test_yml_unified["script"] = clean_code
    else:
        test_yml_unified["script"]["script"] = clean_code

    assert yml_unified == test_yml_unified
    assert script_path == file_path + ".py"


@pytest.mark.parametrize(
    "package_path, dir_name, file_path",
    [
        (
            f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/",
            "Integrations",
            f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB",
        ),
        (
            f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/",
            "Scripts",
            f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/CalculateGeoDistance",
        ),
        (
            f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/",
            "fake_directory",
            f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB",
        ),
    ],
)
def test_insert_script_to_yml_exceptions(package_path, dir_name, file_path):
    is_script_package = dir_name == "Scripts"
    with open(file_path + ".yml") as yml:
        test_yml_data = yaml.load(yml)
    if dir_name == "Scripts":
        test_yml_data["script"] = "blah"
    else:
        test_yml_data["script"]["script"] = "blah"

    IntegrationScriptUnifier.insert_script_to_yml(
        Path(package_path), ".py", {"script": {}}, test_yml_data, is_script_package
    )


def create_test_package(
    test_dir,
    package_name,
    base_yml,
    script_code,
    detailed_description="",
    image_file="",
):
    package_path = os.path.join(test_dir, package_name)

    os.makedirs(package_path)
    shutil.copy(base_yml, os.path.join(package_path, f"{package_name}.yml"))

    with open(os.path.join(package_path, f"{package_name}.py"), "w") as file_:
        file_.write(script_code)

    if detailed_description:
        with open(
            os.path.join(package_path, f"{package_name}_description.md"), "w"
        ) as file_:
            file_.write(detailed_description)

    if image_file:
        shutil.copy(image_file, os.path.join(package_path, f"{package_name}_image.png"))


class TestMergeScriptPackageToYMLIntegration:
    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path):
        self.test_dir_path = str(tmp_path / "Unifier" / "Testing" / "Integrations")
        os.makedirs(self.test_dir_path)
        self.package_name = "SampleIntegPackage"
        self.export_dir_path = os.path.join(self.test_dir_path, self.package_name)
        self.expected_yml_path = os.path.join(
            self.test_dir_path, "integration-SampleIntegPackage.yml"
        )

    def test_unify_integration(self, mocker):
        """
        sanity test of merge_script_package_to_yml of integration
        """

        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml="demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage.yml",
            script_code=TEST_VALID_CODE,
            detailed_description=TEST_VALID_DETAILED_DESCRIPTION,
            image_file="demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage_image.png",
        )

        mocker.patch.object(
            IntegrationScript, "get_supported_native_images", return_value=[]
        )
        export_yml_path = PrepareUploadManager.prepare_for_upload(
            input=Path(self.export_dir_path), output=Path(self.test_dir_path)
        )

        assert export_yml_path == Path(self.expected_yml_path)

        actual_yml = get_yaml(export_yml_path)

        expected_yml = get_yaml(
            "demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/"
            "integration-SampleIntegPackageSanity.yml"
        )

        assert expected_yml == actual_yml

    @pytest.mark.parametrize(
        "marketplace",
        (
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
        ),
    )
    def test_unify_integration__hidden_param(
        self, marketplace: MarketplaceVersions, mocker
    ):
        """
        Given   an integration file with params that have different valid values for the `hidden` attribute
        When    running unify
        Then    make sure the list-type values are replaced with a boolean that matches the marketplace value
                (see the update_hidden_parameters_value docstrings for more information)
        """
        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml="demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackageHiddenParams.yml",
            script_code=TEST_VALID_CODE,
            detailed_description=TEST_VALID_DETAILED_DESCRIPTION,
            image_file="demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage_image.png",
        )

        mocker.patch.object(
            IntegrationScript, "get_supported_native_images", return_value=[]
        )
        unified_yml = PrepareUploadManager.prepare_for_upload(
            input=Path(self.export_dir_path),
            output=Path(self.test_dir_path),
            marketplace=marketplace,
        )

        hidden_true = set()
        hidden_false = set()
        missing_hidden_field = set()

        for param in get_yaml(unified_yml)["configuration"]:
            # updates the three sets
            {True: hidden_true, False: hidden_false, None: missing_hidden_field}[
                param.get("hidden")
            ].add(param["display"])

        assert hidden_true.isdisjoint(hidden_false)
        assert (
            len(missing_hidden_field) == 5
        )  # old params + `Should not be hidden - no hidden attribute`
        assert len(hidden_true | hidden_false) == 8
        assert ("Should be hidden on all XSOAR only" in hidden_true) == (
            marketplace
            in [
                MarketplaceVersions.XSOAR,
                MarketplaceVersions.XSOAR_SAAS,
                MarketplaceVersions.XSOAR_ON_PREM,
            ]
        )
        assert ("Should be hidden on XSIAM only" in hidden_true) == (
            marketplace == MarketplaceVersions.MarketplaceV2
        )
        assert ("Should be hidden on XSOAR_SAAS only" in hidden_true) == (
            marketplace == MarketplaceVersions.XSOAR_SAAS
        )
        assert ("Should be hidden on XSOAR_ON_PREM only" in hidden_true) == (
            marketplace
            in [MarketplaceVersions.XSOAR_ON_PREM, MarketplaceVersions.XSOAR]
        )
        if marketplace in [
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.XSOAR_ON_PREM,
            MarketplaceVersions.XSOAR_SAAS,
        ]:
            assert (
                "Should be hidden on all XSOAR and marketplaceV2 - attribute lists both marketplaces"
                in hidden_true
            )

        if marketplace in [
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XSOAR_SAAS,
        ]:
            assert (
                "Should be hidden on both XSOAR_SAAS and MarketplaceV2" in hidden_true
            )
        else:
            assert (
                "Should be hidden on both XSOAR_SAAS and MarketplaceV2" in hidden_false
            )

        assert "attribute is True Should be hidden in all marketplaces" in hidden_true
        assert "Should not be hidden - hidden attribute is False" in hidden_false
        assert "Should not be hidden - no hidden attribute" in missing_hidden_field

    @pytest.mark.parametrize(
        "marketplace", (MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2)
    )
    def test_unify_integration__hidden_param_type9(
        self, marketplace: MarketplaceVersions, mocker
    ):
        """
        Given   an integration file with params that have credentials param of type 9 with valid values
                for the `hidden` attribute
        When    running unify
        Then    make sure the list-type values are replaced with a boolean that matches the marketplace value
                and `hidden` attribute is replaced with hiddenusername and hiddenpassword.
                (see the update_hidden_parameters_value docstrings for more information)
        """
        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml="demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackageHiddenParams.yml",
            script_code=TEST_VALID_CODE,
            detailed_description=TEST_VALID_DETAILED_DESCRIPTION,
            image_file="demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage_image.png",
        )

        mocker.patch.object(
            IntegrationScript, "get_supported_native_images", return_value=[]
        )
        unified_yml = PrepareUploadManager.prepare_for_upload(
            input=Path(self.export_dir_path),
            output=Path(self.test_dir_path),
            marketplace=marketplace,
        )

        for param in get_yaml(unified_yml)["configuration"]:
            # updates the three sets
            if param["name"] == "credentials":
                assert "hidden" not in param
                assert (param["hiddenusername"]) == (
                    marketplace == MarketplaceVersions.XSOAR
                )
                assert (param["hiddenpassword"]) == (
                    marketplace == MarketplaceVersions.XSOAR
                )

    def test_unify_integration__detailed_description_with_special_char(self, mocker):
        """
        -
        """
        description = """
        some test with special chars
        שלום
        hello
        你好
        """

        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml="demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage.yml",
            script_code=TEST_VALID_CODE,
            image_file="demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage_image.png",
            detailed_description=description,
        )

        mocker.patch.object(
            IntegrationScript, "get_supported_native_images", return_value=[]
        )
        export_yml_path = PrepareUploadManager.prepare_for_upload(
            Path(self.export_dir_path), output=Path(self.test_dir_path)
        )

        assert export_yml_path == Path(self.expected_yml_path)
        actual_yml = get_yaml(export_yml_path)

        expected_yml = get_yaml(
            "demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/"
            "integration-SampleIntegPackageDescSpecialChars.yml"
        )

        assert expected_yml == actual_yml
        assert actual_yml["detaileddescription"] == description

    def test_unify_integration__detailed_description_with_yml_structure(self, mocker):
        """
        -
        """
        description = """ this is a regular line
  some test with special chars
        hello
        key:
          - subkey: hello
            subkey2: hi
        keys: "some more values"
         asd - hello
         hi: 'dsfsd'
final test: hi
"""

        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml="demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage.yml",
            script_code=TEST_VALID_CODE,
            image_file="demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage_image.png",
            detailed_description=description,
        )

        mocker.patch.object(
            IntegrationScript, "get_supported_native_images", return_value=[]
        )
        export_yml_path = PrepareUploadManager.prepare_for_upload(
            Path(self.export_dir_path), output=Path(self.test_dir_path)
        )

        assert export_yml_path == Path(self.expected_yml_path)

        actual_yml = get_yaml(export_yml_path)
        expected_yml = get_yaml(
            "demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/"
            "integration-SampleIntegPackageDescAsYML.yml"
        )

        assert expected_yml == actual_yml
        assert actual_yml["detaileddescription"] == description

    def test_unify_default_output_integration(self, mocker):
        """
        Given
        - UploadTest integration.
        - No output path.

        When
        - Running Unify on it.

        Then
        - Ensure Unify command works with default output.
        """
        input_path_integration = (
            TESTS_DIR + "/test_files/Packs/DummyPack/Integrations/UploadTest"
        )
        mocker.patch.object(
            IntegrationScript, "get_supported_native_images", return_value=[]
        )
        export_yml_path = PrepareUploadManager.prepare_for_upload(
            Path(input_path_integration)
        )
        expected_yml_path = (
            TESTS_DIR
            + "/test_files/Packs/DummyPack/Integrations/UploadTest/integration-UploadTest.yml"
        )

        assert export_yml_path == Path(expected_yml_path)
        Path(expected_yml_path).unlink()


class TestMergeScriptPackageToYMLScript:
    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path):
        self.test_dir_path = str(tmp_path / "Unifier" / "Testing" / "Scripts")
        os.makedirs(self.test_dir_path)
        self.package_name = "SampleScriptPackage"
        self.export_dir_path = os.path.join(self.test_dir_path, self.package_name)
        self.expected_yml_path = os.path.join(
            self.test_dir_path, "script-SampleScriptPackage.yml"
        )

    def test_unify_script(self, mocker):
        """
        sanity test of merge_script_package_to_yml of script
        """

        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml="demisto_sdk/tests/test_files/Unifier/SampleScriptPackage/SampleScriptPackage.yml",
            script_code=TEST_VALID_CODE,
        )

        mocker.patch.object(
            IntegrationScript, "get_supported_native_images", return_value=[]
        )
        export_yml_path = PrepareUploadManager.prepare_for_upload(
            input=Path(self.export_dir_path), output=Path(self.test_dir_path)
        )

        assert export_yml_path == Path(self.expected_yml_path)

        actual_yml = get_yaml(export_yml_path)

        expected_yml = get_yaml(
            "demisto_sdk/tests/test_files/Unifier/SampleScriptPackage/"
            "script-SampleScriptPackageSanity.yml"
        )

        assert expected_yml == actual_yml

    def test_unify_default_output_script(self, mocker):
        """
        Given
        - DummyScript script.
        - No output path.

        When
        - Running Unify on it.

        Then
        - Ensure Unify script works with default output.
        """
        input_path_script = (
            TESTS_DIR + "/test_files/Packs/DummyPack/Scripts/DummyScript"
        )
        mocker.patch.object(
            IntegrationScript, "get_supported_native_images", return_value=[]
        )
        export_yml_path = PrepareUploadManager.prepare_for_upload(
            Path(input_path_script)
        )
        expected_yml_path = (
            TESTS_DIR
            + "/test_files/Packs/DummyPack/Scripts/DummyScript/script-DummyScript.yml"
        )

        assert export_yml_path == Path(expected_yml_path)
        Path(expected_yml_path).unlink()


UNIFY_CMD = "unify"
PARTNER_URL = "https://github.com/bar"
PARTNER_EMAIL = "support@test.com"

PACK_METADATA_PARTNER = json.dumps(
    {
        "name": "test",
        "description": "test",
        "support": "partner",
        "currentVersion": "1.0.1",
        "author": "bar",
        "url": PARTNER_URL,
        "email": PARTNER_EMAIL,
        "categories": ["Data Enrichment & Threat Intelligence"],
        "tags": [],
        "useCases": [],
        "keywords": [],
    }
)
PACK_METADATA_PARTNER_EMAIL_LIST = json.dumps(
    {
        "name": "test",
        "description": "test",
        "support": "partner",
        "currentVersion": "1.0.1",
        "author": "bar",
        "url": PARTNER_URL,
        "email": "support1@test.com,support2@test.com",
        "categories": ["Data Enrichment & Threat Intelligence"],
        "tags": [],
        "useCases": [],
        "keywords": [],
    }
)
PACK_METADATA_STRINGS_EMAIL_LIST = json.dumps(
    {
        "name": "test",
        "description": "test",
        "support": "partner",
        "currentVersion": "1.0.1",
        "author": "bar",
        "url": PARTNER_URL,
        "email": "['support1@test.com', 'support2@test.com']",
        "categories": ["Data Enrichment & Threat Intelligence"],
        "tags": [],
        "useCases": [],
        "keywords": [],
    }
)
PACK_METADATA_PARTNER_NO_EMAIL = json.dumps(
    {
        "name": "test",
        "description": "test",
        "support": "partner",
        "currentVersion": "1.0.1",
        "author": "bar",
        "url": PARTNER_URL,
        "email": "",
        "categories": ["Data Enrichment & Threat Intelligence"],
        "tags": [],
        "useCases": [],
        "keywords": [],
    }
)
PACK_METADATA_PARTNER_NO_URL = json.dumps(
    {
        "name": "test",
        "description": "test",
        "support": "partner",
        "currentVersion": "1.0.1",
        "author": "bar",
        "url": "",
        "email": PARTNER_EMAIL,
        "categories": ["Data Enrichment & Threat Intelligence"],
        "tags": [],
        "useCases": [],
        "keywords": [],
    }
)
PACK_METADATA_XSOAR = json.dumps(
    {
        "name": "test",
        "description": "test",
        "support": "xsoar",
        "currentVersion": "1.0.0",
        "author": "Cortex XSOAR",
        "url": "https://www.paloaltonetworks.com/cortex",
        "email": "",
        "categories": ["Endpoint"],
        "tags": [],
        "useCases": [],
        "keywords": [],
    }
)

PACK_METADATA_COMMUNITY = json.dumps(
    {
        "name": "test",
        "description": "test",
        "support": "community",
        "currentVersion": "1.0.0",
        "author": "Community Contributor",
        "url": "",
        "email": "",
        "categories": ["Endpoint"],
        "tags": [],
        "useCases": [],
        "keywords": [],
    }
)

PARTNER_UNIFY = {
    "script": {},
    "type": "python",
    "image": "image",
    "detaileddescription": "test details",
    "display": "test",
}
PARTNER_UNIFY_NO_EMAIL = PARTNER_UNIFY.copy()
PARTNER_UNIFY_NO_URL = PARTNER_UNIFY.copy()
XSOAR_UNIFY = PARTNER_UNIFY.copy()
COMMUNITY_UNIFY = PARTNER_UNIFY.copy()
PARTNER_UNIFY_EMAIL_LIST = PARTNER_UNIFY.copy()

INTEGRATION_YAML = {
    "commonfields": {"id": "IntegrationName"},
    "name": "IntegrationName",
    "display": "test",
    "category": "test",
    "script": {"type": "python", "script": "import abc"},
}

PARTNER_DISPLAY_NAME = "test (Partner Contribution)"
COMMUNITY_DISPLAY_NAME = "test (Community Contribution)"
PARTNER_DETAILEDDESCRIPTION = (
    "### This is a partner contributed integration"
    f"\nFor all questions and enhancement requests please contact the partner directly:"
    f"\n**Email** - [mailto](mailto:{PARTNER_EMAIL})\n**URL** - [{PARTNER_URL}]({PARTNER_URL})\n***\ntest details"
)
PARTNER_DETAILEDDESCRIPTION_NO_EMAIL = (
    "### This is a partner contributed integration"
    f"\nFor all questions and enhancement requests please contact the partner directly:"
    f"\n**URL** - [{PARTNER_URL}]({PARTNER_URL})\n***\ntest details"
)
PARTNER_DETAILEDDESCRIPTION_NO_URL = (
    "### This is a partner contributed integration"
    f"\nFor all questions and enhancement requests please contact the partner directly:"
    f"\n**Email** - [mailto](mailto:{PARTNER_EMAIL})\n***\ntest details"
)


def test_unify_partner_contributed_pack(mocker, monkeypatch, repo):
    """
    Given
        - Partner contributed pack with email and url in the support details.
    When
        - Running unify on it.
    Then
        - Ensure unify create unified file with partner support notes.
    """
    mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    logger_debug = mocker.patch.object(logging.getLogger("demisto-sdk"), "debug")
    monkeypatch.setenv("COLUMNS", "1000")

    pack = repo.create_pack("PackName")
    integration = pack.create_integration("integration", "bla", INTEGRATION_YAML)
    pack.pack_metadata.write_json(PACK_METADATA_PARTNER)
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_script_to_yml",
        return_value=(PARTNER_UNIFY, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_image_to_yml",
        return_value=(PARTNER_UNIFY, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_description_to_yml",
        return_value=(PARTNER_UNIFY, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "get_data",
        return_value=(PACK_METADATA_PARTNER, pack.pack_metadata.path),
    )

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        runner.invoke(
            main,
            [UNIFY_CMD, "-i", integration.path, "-o", integration.path],
            catch_exceptions=True,
        )
    # Verifying unified process
    assert str_in_call_args_list(logger_debug.call_args_list, "Created unified yml:")

    # Verifying the unified file data
    assert PARTNER_UNIFY["display"] == PARTNER_DISPLAY_NAME
    assert "#### Integration Author:" in PARTNER_UNIFY["detaileddescription"]
    assert "Email" in PARTNER_UNIFY["detaileddescription"]
    assert "URL" in PARTNER_UNIFY["detaileddescription"]


def test_unify_partner_contributed_pack_no_email(mocker, monkeypatch, repo):
    """
    Given
        - Partner contributed pack with url and without email in the support details.
    When
        - Running unify on it.
    Then
        - Ensure unify create unified file with partner support notes.
    """
    mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    logger_debug = mocker.patch.object(logging.getLogger("demisto-sdk"), "debug")
    monkeypatch.setenv("COLUMNS", "1000")

    pack = repo.create_pack("PackName")
    integration = pack.create_integration("integration", "bla", INTEGRATION_YAML)
    pack.pack_metadata.write_json(PACK_METADATA_PARTNER_NO_EMAIL)
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_script_to_yml",
        return_value=(PARTNER_UNIFY_NO_EMAIL, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_image_to_yml",
        return_value=(PARTNER_UNIFY_NO_EMAIL, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_description_to_yml",
        return_value=(PARTNER_UNIFY_NO_EMAIL, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "get_data",
        return_value=(PACK_METADATA_PARTNER_NO_EMAIL, pack.pack_metadata.path),
    )

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        runner.invoke(
            main,
            [UNIFY_CMD, "-i", integration.path, "-o", integration.path],
            catch_exceptions=True,
        )
    # Verifying unified process
    assert str_in_call_args_list(logger_debug.call_args_list, "Created unified yml:")

    # Verifying the unified file data
    assert PARTNER_UNIFY_NO_EMAIL["display"] == PARTNER_DISPLAY_NAME
    assert "#### Integration Author:" in PARTNER_UNIFY_NO_EMAIL["detaileddescription"]
    assert "Email" not in PARTNER_UNIFY_NO_EMAIL["detaileddescription"]
    assert "URL" in PARTNER_UNIFY_NO_EMAIL["detaileddescription"]


@pytest.mark.parametrize(
    argnames="pack_metadata",
    argvalues=[PACK_METADATA_PARTNER_EMAIL_LIST, PACK_METADATA_STRINGS_EMAIL_LIST],
)
def test_unify_contributor_emails_list(mocker, repo, pack_metadata):
    """
    Given
        - Partner contributed pack with email list and url in the support details.
    When
        - Running unify on it.
    Then
        - Ensure unify create a unified file with partner support email list.
    """
    pack = repo.create_pack("PackName")
    integration = pack.create_integration("integration", "bla", INTEGRATION_YAML)
    pack.pack_metadata.write_json(pack_metadata)
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_image_to_yml",
        return_value=(PARTNER_UNIFY_EMAIL_LIST, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_description_to_yml",
        return_value=(PARTNER_UNIFY_EMAIL_LIST, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "get_data",
        return_value=(pack_metadata, pack.pack_metadata.path),
    )

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        runner.invoke(
            main,
            [UNIFY_CMD, "-i", integration.path, "-o", integration.path],
            catch_exceptions=True,
        )
    # Verifying the unified file data
    assert (
        "**Email**: [support1@test.com]"
        in PARTNER_UNIFY_EMAIL_LIST["detaileddescription"]
    )
    assert (
        "**Email**: [support2@test.com]"
        in PARTNER_UNIFY_EMAIL_LIST["detaileddescription"]
    )


def test_unify_partner_contributed_pack_no_url(mocker, monkeypatch, repo):
    """
    Given
        - Partner contributed pack with email and without url in the support details
    When
        - Running unify on it.
    Then
        - Ensure unify create unified file with partner support notes.
    """
    mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    logger_debug = mocker.patch.object(logging.getLogger("demisto-sdk"), "debug")
    monkeypatch.setenv("COLUMNS", "1000")

    pack = repo.create_pack("PackName")
    integration = pack.create_integration("integration", "bla", INTEGRATION_YAML)
    pack.pack_metadata.write_json(PACK_METADATA_PARTNER_NO_URL)
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_script_to_yml",
        return_value=(PARTNER_UNIFY_NO_URL, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_image_to_yml",
        return_value=(PARTNER_UNIFY_NO_URL, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_description_to_yml",
        return_value=(PARTNER_UNIFY_NO_URL, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "get_data",
        return_value=(PACK_METADATA_PARTNER_NO_URL, pack.pack_metadata.path),
    )

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        runner.invoke(
            main,
            [UNIFY_CMD, "-i", integration.path, "-o", integration.path],
            catch_exceptions=True,
        )
    # Verifying unified process
    assert str_in_call_args_list(logger_debug.call_args_list, "Created unified yml:")

    # Verifying the unified file data
    assert PARTNER_UNIFY_NO_URL["display"] == PARTNER_DISPLAY_NAME
    assert "#### Integration Author:" in PARTNER_UNIFY_NO_URL["detaileddescription"]
    assert "Email" in PARTNER_UNIFY_NO_URL["detaileddescription"]
    assert "URL" not in PARTNER_UNIFY_NO_URL["detaileddescription"]


def test_unify_not_partner_contributed_pack(mocker, monkeypatch, repo):
    """
    Given
        - XSOAR supported - not a partner contribution
    When
        - Running unify on it.
    Then
        - Ensure unify create unified file without partner support notes.
    """
    mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    logger_debug = mocker.patch.object(logging.getLogger("demisto-sdk"), "debug")
    monkeypatch.setenv("COLUMNS", "1000")

    pack = repo.create_pack("PackName")
    integration = pack.create_integration("integration", "bla", INTEGRATION_YAML)
    pack.pack_metadata.write_json(PACK_METADATA_XSOAR)
    mocker.patch.object(
        IntegrationScriptUnifier, "insert_script_to_yml", return_value=(XSOAR_UNIFY, "")
    )
    mocker.patch.object(
        IntegrationScriptUnifier, "insert_image_to_yml", return_value=(XSOAR_UNIFY, "")
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_description_to_yml",
        return_value=(XSOAR_UNIFY, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "get_data",
        return_value=(PACK_METADATA_XSOAR, pack.pack_metadata.path),
    )

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        runner.invoke(
            main,
            [UNIFY_CMD, "-i", integration.path, "-o", integration.path],
            catch_exceptions=True,
        )
    # Verifying unified process
    assert str_in_call_args_list(logger_debug.call_args_list, "Created unified yml:")

    # Verifying the unified file data
    assert "Partner" not in XSOAR_UNIFY["display"]
    assert "partner" not in XSOAR_UNIFY["detaileddescription"]


def test_unify_community_contributed(mocker, monkeypatch, repo):
    """
    Given
        - Community contribution.
    When
        - Running unify on it.
    Then
        - Ensure unify create unified file with community detailed description.
    """
    mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    logger_debug = mocker.patch.object(logging.getLogger("demisto-sdk"), "debug")
    monkeypatch.setenv("COLUMNS", "1000")

    pack = repo.create_pack("PackName")
    integration = pack.create_integration("integration", "bla", INTEGRATION_YAML)
    pack.pack_metadata.write_json(PACK_METADATA_COMMUNITY)
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_script_to_yml",
        return_value=(COMMUNITY_UNIFY, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_image_to_yml",
        return_value=(COMMUNITY_UNIFY, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "insert_description_to_yml",
        return_value=(COMMUNITY_UNIFY, ""),
    )
    mocker.patch.object(
        IntegrationScriptUnifier,
        "get_data",
        return_value=(PACK_METADATA_COMMUNITY, pack.pack_metadata.path),
    )

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        runner.invoke(
            main,
            [UNIFY_CMD, "-i", integration.path, "-o", integration.path],
            catch_exceptions=True,
        )
    # Verifying unified process
    assert str_in_call_args_list(logger_debug.call_args_list, "Created unified yml:")

    # Verifying the unified file data
    assert COMMUNITY_UNIFY["display"] == COMMUNITY_DISPLAY_NAME
    assert "#### Integration Author:" in COMMUNITY_UNIFY["detaileddescription"]
    assert (
        "No support or maintenance is provided by the author."
        in COMMUNITY_UNIFY["detaileddescription"]
    )


def test_add_contributors_support(tmp_path):
    """
    Given:
        - partner integration which have (Partner Contribution) in the integration display name

    When:
        - Adding contribution support to display name

    Then:
        - Verify CONTRIBUTOR_DISPLAY_NAME is not added twice
    """
    unified_yml = {
        "display": "Test Integration (Partner Contribution)",
        "commonfields": {"id": "Test Integration"},
    }

    IntegrationScriptUnifier.add_contributors_support(
        unified_yml=unified_yml,
        contributor_type="partner",
        contributor_email="",
        contributor_url="",
    )
    assert unified_yml["display"] == "Test Integration (Partner Contribution)"


def test_add_custom_section(tmp_path):
    """
    Given:
        - an Integration to unify

    When:
        - the --custom flag is True

    Then:
        - Add a "Test" to the name/display/id of the integration if the yml exsits.
    """
    unified_yml = {
        "display": "Integration display",
        "commonfields": {"id": "Integration id"},
        "name": "Integration name",
    }
    unified = IntegrationScriptUnifier.add_custom_section(unified_yml, "Test", False)
    assert unified.get("display") == "Integration display - Test"
    assert unified.get("name") == "Integration name - Test"
    assert unified.get("commonfields").get("id") == "Integration id - Test"


def test_empty_yml(tmp_path):
    """
    Given:
        - An empty unified yml

    When:
        - calling the add_custom_section when using the -t flag

    Then:
        - Check that the function will not raise any errors.
    """
    IntegrationScriptUnifier.add_custom_section({})


def test_update_hidden_parameters_value():
    """
    Given:
        - An xsoar marketplace and yml dict data

    When:
        - Updatining the value of the hidden parameter

    Then:
        - Validate if xsoar_on_prem hidden tag the marketplace will be hidden in xsoar
        - Validate if xsoar hidden tag the marketplace will be hidden in xsoar
        - Validate if xsoar_saas tag the marketplace will not be hidden in xsoar"""
    yml_data = {
        "configuration": [
            {"param1": "", "hidden": ["xsoar_on_prem"]},
            {"param2": "", "hidden": ["xsoar"]},
            {"param3": "", "hidden": ["xsoar_saas"]},
        ]
    }
    IntegrationScriptUnifier.update_hidden_parameters_value(
        yml_data, MarketplaceVersions.XSOAR
    )
    assert yml_data["configuration"][0]["hidden"] is True
    assert yml_data["configuration"][1]["hidden"] is True
    assert yml_data["configuration"][2]["hidden"] is False
