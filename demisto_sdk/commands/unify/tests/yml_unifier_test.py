import base64
import copy
import json
import os
import re
import shutil

import pytest
import requests
import yaml
import yamlordereddictloader
from click.testing import CliRunner
from mock import patch

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.commands.unify.yml_unifier import YmlUnifier
from TestSuite.test_tools import ChangeCWD

TEST_VALID_CODE = '''import demistomock as demisto
from CommonServerPython import *

def main():
    return_error('Not implemented.')
​
if __name__ in ('builtins', '__builtin__', '__main__'):
    main()
'''

TEST_VALID_DETAILED_DESCRIPTION = '''first line
second line

## header1
do the following:
1. say hello
2. say goodbye
'''

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

    if __name__ in ["builtins", "__main__"]:
        main()
    '''

DUMMY_MODULE = '''
import requests
import base64
from typing import Dict, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

OPROXY_AUTH_TYPE = 'oproxy'
SELF_DEPLOYED_AUTH_TYPE = 'self_deployed'


class MicrosoftClient(BaseClient):

    def __init__(self, tenant_id: str = '', auth_id: str = '', enc_key: str = '',
                 token_retrieval_url: str = '', app_name: str = '', refresh_token: str = '',
                 client_id: str = '', client_secret: str = '', scope: str = '', resource: str = '', app_url: str = '',
                 verify: bool = True, auth_type: str = OPROXY_AUTH_TYPE, *args, **kwargs):

'''

TESTS_DIR = f'{git_path()}/demisto_sdk/tests'


def test_clean_python_code(repo):
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration', 'bla', INTEGRATION_YAML)
    unifier = YmlUnifier(str(integration.path))
    script_code = "import demistomock as demisto\nfrom CommonServerPython import *  # test comment being removed\n" \
                  "from CommonServerUserPython import *\nfrom __future__ import print_function"
    # Test remove_print_future is False
    script_code = unifier.clean_python_code(script_code, remove_print_future=False)
    assert script_code == "\n\n\nfrom __future__ import print_function"
    # Test remove_print_future is True
    script_code = unifier.clean_python_code(script_code)
    assert script_code.strip() == ""


def test_get_code_file():
    # Test integration case
    unifier = YmlUnifier(f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/")
    assert unifier.get_code_file(".py") == f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB.py"
    unifier = YmlUnifier(f"{git_path()}/demisto_sdk/tests/test_files/Unifier/SampleNoPyFile")
    with pytest.raises(Exception):
        unifier.get_code_file(".py")
    # Test script case
    unifier = YmlUnifier(f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/")
    assert unifier.get_code_file(".py") == f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/" \
                                           f"CalculateGeoDistance.py"


def test_get_code_file_case_insensative(tmp_path):
    # Create an integration dir with some files
    integration_dir = tmp_path / "TestDummyInt"
    os.makedirs(integration_dir)
    open(integration_dir / "Dummy.ps1", 'a')
    open(integration_dir / "ADummy.tests.ps1", 'a')  # a test file which is named such a way that it comes up first
    unifier = YmlUnifier(str(integration_dir))
    assert unifier.get_code_file(".ps1") == str(integration_dir / "Dummy.ps1")


def test_get_script_or_integration_package_data():
    unifier = YmlUnifier(f"{git_path()}/demisto_sdk/tests/test_files/Unifier/SampleNoPyFile")
    with pytest.raises(Exception):
        unifier.get_script_or_integration_package_data()
    unifier = YmlUnifier(f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance")
    with open(f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/CalculateGeoDistance.py", "r") as \
            code_file:
        code = code_file.read()
    yml_path, code_data = unifier.get_script_or_integration_package_data()
    assert yml_path == f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/CalculateGeoDistance.yml"
    assert code_data == code


def test_get_data():
    with patch.object(YmlUnifier, "__init__", lambda a, b, c, d, e: None):
        unifier = YmlUnifier('', None, None, None)
        unifier.package_path = f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/"
        unifier.is_script_package = False
        with open(f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_image.png", "rb") as image_file:
            image = image_file.read()
        data, found_data_path = unifier.get_data(unifier.package_path, "*png")
        assert data == image
        assert found_data_path == f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_image.png"
        unifier.is_script_package = True
        data, found_data_path = unifier.get_data(unifier.package_path, "*png")
        assert data is None
        assert found_data_path is None


def test_insert_description_to_yml():
    with patch.object(YmlUnifier, "__init__", lambda a, b, c, d, e: None):
        unifier = YmlUnifier('', None, None, None)
        unifier.package_path = f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/"
        unifier.dir_name = "Integrations"
        unifier.is_script_package = False
        with open(f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_description.md", "rb") as desc_file:
            desc_data = desc_file.read().decode("utf-8")
        integration_doc_link = '\n\n---\n[View Integration Documentation]' \
                               '(https://xsoar.pan.dev/docs/reference/integrations/vuln-db)'
        yml_unified, found_data_path = unifier.insert_description_to_yml(
            {'commonfields': {'id': 'VulnDB'}}, {}
        )

        assert found_data_path == f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_description.md"
        assert (desc_data + integration_doc_link) == yml_unified['detaileddescription']


def test_insert_description_to_yml_with_no_detailed_desc(tmp_path):
    """
        Given:
            - Integration with empty detailed description and with non-empty README

        When:
            - Inserting detailed description to the unified integration YAML

        Then:
            - Verify the integration doc markdown link is inserted to the detailed description
        """
    readme = tmp_path / 'README.md'
    readme.write_text('README')
    detailed_desc = tmp_path / 'integration_description.md'
    detailed_desc.write_text('')
    unifier = YmlUnifier(str(tmp_path))
    yml_unified, _ = unifier.insert_description_to_yml({'commonfields': {'id': 'some integration id'}}, {})
    assert '[View Integration Documentation](https://xsoar.pan.dev/docs/reference/integrations/some-integration-id)'\
           == yml_unified['detaileddescription']


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
    readme = tmp_path / 'README.md'
    readme.write_text('README')
    unifier = YmlUnifier(str(tmp_path))
    integration_doc_link = unifier.get_integration_doc_link({'commonfields': {'id': 'Cortex XDR - IOC'}})
    assert integration_doc_link == \
        '[View Integration Documentation](https://xsoar.pan.dev/docs/reference/integrations/cortex-xdr---ioc)'
    link = re.findall(r'\(([^)]+)\)', integration_doc_link)[0]
    try:
        r = requests.get(link, verify=False, timeout=10)
        r.raise_for_status()
    except requests.HTTPError as ex:
        raise Exception(f'Failed reaching to integration doc link {link} - {ex}')


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
    unifier = YmlUnifier(str(tmp_path))
    integration_doc_link = unifier.get_integration_doc_link({'commonfields': {'id': 'Integration With No README'}})
    assert integration_doc_link == ''

    readme = tmp_path / 'README.md'
    readme.write_text('')
    integration_doc_link = unifier.get_integration_doc_link({'commonfields': {'id': 'Integration With Empty README'}})
    assert integration_doc_link == ''


def test_get_integration_doc_link_exist_in_readme(tmp_path):
    """
    Given:
        - integration which have README in the integration dir, with "View Integration Documentation" doc link

    When:
        - Getting integration doc link

    Then:
        - Verify an empty string is returned
    """
    unifier = YmlUnifier(str(tmp_path))

    doc_link = '\n\n---\n[View Integration Documentation]' \
               '(https://xsoar.pan.dev/docs/reference/integrations/integration-readme-with-link)'
    integration_doc_link = unifier.get_integration_doc_link(
        {'commonfields': {'id': 'Integration README with link'}},
        doc_link
    )
    assert integration_doc_link == ''


def test_insert_image_to_yml():
    with patch.object(YmlUnifier, "__init__", lambda a, b, c, d, e: None):
        unifier = YmlUnifier('', None, None, None)
        unifier.package_path = f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/"
        unifier.dir_name = "Integrations"
        unifier.is_script_package = False
        unifier.image_prefix = "data:image/png;base64,"
        with open(f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_image.png", "rb") as image_file:
            image_data = image_file.read()
            image_data = unifier.image_prefix + base64.b64encode(image_data).decode('utf-8')
        with open(f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB.yml", mode="r", encoding="utf-8") \
                as yml_file:
            yml_unified_test = yaml.load(yml_file, Loader=yamlordereddictloader.SafeLoader)
        with open(f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB.yml", "r") as yml:
            yml_data = yaml.safe_load(yml)
        yml_unified, found_img_path = unifier.insert_image_to_yml(yml_data, yml_unified_test)
        yml_unified_test['image'] = image_data
        assert found_img_path == f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_image.png"
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
    integration_dir = tmp_path / 'Integrations'
    integration_dir.mkdir()
    integration_yml = integration_dir / 'SomeIntegration.yml'
    integration_obj = {'id': 'SomeIntegration'}
    yaml.dump(integration_obj, integration_yml.open('w'), default_flow_style=False)
    unifier = YmlUnifier(str(integration_dir))
    yml_unified, found_img_path = unifier.insert_image_to_yml(integration_obj, integration_obj)
    assert yml_unified == integration_obj
    assert not found_img_path


def test_check_api_module_imports():
    module_import, module_name = YmlUnifier.check_api_module_imports(DUMMY_SCRIPT)

    assert module_import == 'from MicrosoftApiModule import *  # noqa: E402'
    assert module_name == 'MicrosoftApiModule'


@pytest.mark.parametrize('import_name', ['from MicrosoftApiModule import *  # noqa: E402',
                                         'from MicrosoftApiModule import *'])
def test_insert_module_code(mocker, import_name):
    mocker.patch.object(YmlUnifier, '_get_api_module_code', return_value=DUMMY_MODULE)
    module_name = 'MicrosoftApiModule'
    new_code = DUMMY_SCRIPT.replace(import_name, '\n### GENERATED CODE ###\n# This code was inserted in place of an API'
                                                 ' module.{}\n'.format(DUMMY_MODULE))

    code = YmlUnifier.insert_module_code(DUMMY_SCRIPT, import_name, module_name)

    assert code == new_code


@pytest.mark.parametrize('package_path, dir_name, file_path', [
    (f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/", "Integrations", f"{git_path()}/demisto_sdk/tests/test_files/"
                                                                           f"VulnDB/VulnDB"),
    (f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/", "Scripts",
     f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/CalculateGeoDistance")])
def test_insert_script_to_yml(package_path, dir_name, file_path):
    with patch.object(YmlUnifier, "__init__", lambda a, b, c, d, e: None):
        unifier = YmlUnifier("", None, None, None)
        unifier.package_path = package_path
        unifier.dir_name = dir_name
        unifier.is_script_package = dir_name == 'Scripts'
        with open(file_path + ".yml", "r") as yml:
            test_yml_data = yaml.safe_load(yml)

        test_yml_unified = copy.deepcopy(test_yml_data)

        yml_unified, script_path = unifier.insert_script_to_yml(".py", test_yml_unified, test_yml_data)

        with open(file_path + ".py", mode="r", encoding="utf-8") as script_file:
            script_code = script_file.read()
        clean_code = unifier.clean_python_code(script_code)

        if isinstance(test_yml_unified.get('script', {}), str):
            test_yml_unified['script'] = clean_code
        else:
            test_yml_unified['script']['script'] = clean_code

        assert yml_unified == test_yml_unified
        assert script_path == file_path + ".py"


@pytest.mark.parametrize('package_path, dir_name, file_path', [
    (f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/", "Integrations",
     f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB"),
    (f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/", "Scripts",
     f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/CalculateGeoDistance"),
    (f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/", "fake_directory",
     f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB"),
])
def test_insert_script_to_yml_exceptions(package_path, dir_name, file_path):
    with patch.object(YmlUnifier, "__init__", lambda a, b, c, d, e: None):
        unifier = YmlUnifier("", None, None, None)
        unifier.package_path = package_path
        unifier.dir_name = dir_name
        unifier.is_script_package = dir_name == 'Scripts'
        with open(file_path + ".yml", "r") as yml:
            test_yml_data = yaml.safe_load(yml)
        if dir_name == "Scripts":
            test_yml_data['script'] = 'blah'
        else:
            test_yml_data['script']['script'] = 'blah'

        unifier.insert_script_to_yml(".py", {'script': {}}, test_yml_data)


def create_test_package(test_dir, package_name, base_yml, script_code, detailed_description='', image_file=''):
    package_path = os.path.join(test_dir, package_name)

    os.makedirs(package_path)
    shutil.copy(base_yml, os.path.join(package_path, f'{package_name}.yml'))

    with open(os.path.join(package_path, f'{package_name}.py'), 'w') as file_:
        file_.write(script_code)

    if detailed_description:
        with open(os.path.join(package_path, f'{package_name}_description.md'), 'w') as file_:
            file_.write(detailed_description)

    if image_file:
        shutil.copy(image_file, os.path.join(package_path, f'{package_name}_image.png'))


class TestMergeScriptPackageToYMLIntegration:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.test_dir_path = str(tmp_path / 'Unifier' / 'Testing')
        os.makedirs(self.test_dir_path)
        self.package_name = 'SampleIntegPackage'
        self.export_dir_path = os.path.join(self.test_dir_path, self.package_name)
        self.expected_yml_path = os.path.join(self.test_dir_path, 'integration-SampleIntegPackage.yml')

    def test_unify_integration(self):
        """
        sanity test of merge_script_package_to_yml of integration
        """

        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml='demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage.yml',
            script_code=TEST_VALID_CODE,
            detailed_description=TEST_VALID_DETAILED_DESCRIPTION,
            image_file='demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage_image.png',
        )

        unifier = YmlUnifier(input=self.export_dir_path, output=self.test_dir_path)
        yml_files = unifier.merge_script_package_to_yml()
        export_yml_path = yml_files[0]

        assert export_yml_path == self.expected_yml_path

        comment = '# this is a comment text inside a file 033dab25fd9655480dbec3a4c579a0e6'
        with open(export_yml_path) as file_:
            unified_content = file_.read()
        assert comment in unified_content

        actual_yml = get_yaml(export_yml_path)

        expected_yml = get_yaml('demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/'
                                'integration-SampleIntegPackageSanity.yml')

        assert expected_yml == actual_yml

    def test_unify_integration__detailed_description_with_special_char(self):
        """
        -
        """
        description = '''
        some test with special chars
        שלום
        hello
        你好
        '''

        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml='demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage.yml',
            script_code=TEST_VALID_CODE,
            image_file='demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage_image.png',
            detailed_description=description,
        )

        unifier = YmlUnifier(self.export_dir_path, output=self.test_dir_path)
        yml_files = unifier.merge_script_package_to_yml()
        export_yml_path = yml_files[0]

        assert export_yml_path == self.expected_yml_path
        actual_yml = get_yaml(export_yml_path)

        expected_yml = get_yaml('demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/'
                                'integration-SampleIntegPackageDescSpecialChars.yml')

        assert expected_yml == actual_yml
        assert actual_yml['detaileddescription'] == description

    def test_unify_integration__detailed_description_with_yml_structure(self):
        """
        -
        """
        description = ''' this is a regular line
  some test with special chars
        hello
        key:
          - subkey: hello
            subkey2: hi
        keys: "some more values"
         asd - hello
         hi: 'dsfsd'
final test: hi
'''

        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml='demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage.yml',
            script_code=TEST_VALID_CODE,
            image_file='demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage_image.png',
            detailed_description=description,
        )

        unifier = YmlUnifier(self.export_dir_path, output=self.test_dir_path)
        yml_files = unifier.merge_script_package_to_yml()
        export_yml_path = yml_files[0]

        assert export_yml_path == self.expected_yml_path

        actual_yml = get_yaml(export_yml_path)
        expected_yml = get_yaml('demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/'
                                'integration-SampleIntegPackageDescAsYML.yml')

        assert expected_yml == actual_yml
        assert actual_yml['detaileddescription'] == description

    def test_unify_default_output_integration(self):
        """
        Given
        - UploadTest integration.
        - No output path.

        When
        - Running Unify on it.

        Then
        - Ensure Unify command works with default output.
        """
        input_path_integration = TESTS_DIR + '/test_files/Packs/DummyPack/Integrations/UploadTest'
        unifier = YmlUnifier(input_path_integration)
        yml_files = unifier.merge_script_package_to_yml()
        export_yml_path = yml_files[0]
        expected_yml_path = TESTS_DIR + '/test_files/Packs/DummyPack/Integrations/UploadTest/integration-UploadTest.yml'

        assert export_yml_path == expected_yml_path
        os.remove(expected_yml_path)

    def test_unify_default_output_integration_for_relative_current_dir_input(self, mocker):
        """
        Given
        - Input path of '.'.
        - UploadTest integration.

        When
        - Running Unify on it.

        Then
        - Ensure Unify command works with default output given relative path to current directory.
        """
        from demisto_sdk.commands.unify.yml_unifier import YmlUnifier
        abs_path_mock = mocker.patch('demisto_sdk.commands.unify.yml_unifier.os.path.abspath')
        abs_path_mock.return_value = TESTS_DIR + '/test_files/Packs/DummyPack/Integrations/UploadTest'
        input_path_integration = '.'
        unifier = YmlUnifier(input_path_integration)
        yml_files = unifier.merge_script_package_to_yml()
        export_yml_path = yml_files[0]
        expected_yml_path = TESTS_DIR + '/test_files/Packs/DummyPack/Integrations/UploadTest/integration-UploadTest.yml'

        assert export_yml_path == expected_yml_path
        os.remove(expected_yml_path)


class TestMergeScriptPackageToYMLScript:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.test_dir_path = str(tmp_path / 'Unifier' / 'Testing')
        os.makedirs(self.test_dir_path)
        self.package_name = 'SampleScriptPackage'
        self.export_dir_path = os.path.join(self.test_dir_path, self.package_name)
        self.expected_yml_path = os.path.join(self.test_dir_path, 'script-SampleScriptPackage.yml')

    def test_unify_script(self):
        """
        sanity test of merge_script_package_to_yml of script
        """

        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml='demisto_sdk/tests/test_files/Unifier/SampleScriptPackage/SampleScriptPackage.yml',
            script_code=TEST_VALID_CODE,
        )

        unifier = YmlUnifier(input=self.export_dir_path, output=self.test_dir_path)
        yml_files = unifier.merge_script_package_to_yml()
        export_yml_path = yml_files[0]

        assert export_yml_path == self.expected_yml_path

        actual_yml = get_yaml(export_yml_path)

        expected_yml = get_yaml('demisto_sdk/tests/test_files/Unifier/SampleScriptPackage/'
                                'script-SampleScriptPackageSanity.yml')

        assert expected_yml == actual_yml

    def test_unify_script__docker45(self):
        """
        sanity test of merge_script_package_to_yml of script
        """

        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml='demisto_sdk/tests/test_files/Unifier/SampleScriptPackage/SampleScriptPackageDocker45.yml',
            script_code=TEST_VALID_CODE,
        )

        unifier = YmlUnifier(input=self.export_dir_path, output=self.test_dir_path)
        yml_files = unifier.merge_script_package_to_yml()
        assert len(yml_files) == 2
        export_yml_path = yml_files[0]
        export_yml_path_45 = yml_files[1]

        assert export_yml_path == self.expected_yml_path
        assert export_yml_path_45 == self.expected_yml_path.replace('.yml', '_45.yml')

        actual_yml = get_yaml(export_yml_path)

        expected_yml = get_yaml('demisto_sdk/tests/test_files/Unifier/SampleScriptPackage/'
                                'script-SampleScriptPackageSanityDocker45.yml')

        assert expected_yml == actual_yml

        actual_yml_45 = get_yaml(export_yml_path_45)

        expected_yml_45 = get_yaml('demisto_sdk/tests/test_files/Unifier/SampleScriptPackage/'
                                   'script-SampleScriptPackageSanityDocker45_45.yml')
        assert expected_yml_45 == actual_yml_45

    def test_unify_default_output_script(self):
        """
        Given
        - DummyScript script.
        - No output path.

        When
        - Running Unify on it.

        Then
        - Ensure Unify script works with default output.
        """
        input_path_script = TESTS_DIR + '/test_files/Packs/DummyPack/Scripts/DummyScript'
        unifier = YmlUnifier(input_path_script)
        yml_files = unifier.merge_script_package_to_yml()
        export_yml_path = yml_files[0]
        expected_yml_path = TESTS_DIR + '/test_files/Packs/DummyPack/Scripts/DummyScript/script-DummyScript.yml'

        assert export_yml_path == expected_yml_path
        os.remove(expected_yml_path)


UNIFY_CMD = 'unify'
PARTNER_URL = "https://github.com/bar"
PARTNER_EMAIL = "support@test.com"

PACK_METADATA_PARTNER = json.dumps({
    "name": "test",
    "description": "test",
    "support": "partner",
    "currentVersion": "1.0.1",
    "author": "bar",
    "url": PARTNER_URL,
    "email": PARTNER_EMAIL,
    "categories": [
        "Data Enrichment & Threat Intelligence"
    ],
    "tags": [],
    "useCases": [],
    "keywords": []
})
PACK_METADATA_PARTNER_EMAIL_LIST = json.dumps({
    "name": "test",
    "description": "test",
    "support": "partner",
    "currentVersion": "1.0.1",
    "author": "bar",
    "url": PARTNER_URL,
    "email": "support1@test.com,support2@test.com",
    "categories": [
        "Data Enrichment & Threat Intelligence"
    ],
    "tags": [],
    "useCases": [],
    "keywords": []
})
PACK_METADATA_STRINGS_EMAIL_LIST = json.dumps({
    "name": "test",
    "description": "test",
    "support": "partner",
    "currentVersion": "1.0.1",
    "author": "bar",
    "url": PARTNER_URL,
    "email": "['support1@test.com', 'support2@test.com']",
    "categories": [
        "Data Enrichment & Threat Intelligence"
    ],
    "tags": [],
    "useCases": [],
    "keywords": []
})
PACK_METADATA_PARTNER_NO_EMAIL = json.dumps({
    "name": "test",
    "description": "test",
    "support": "partner",
    "currentVersion": "1.0.1",
    "author": "bar",
    "url": PARTNER_URL,
    "email": '',
    "categories": [
        "Data Enrichment & Threat Intelligence"
    ],
    "tags": [],
    "useCases": [],
    "keywords": []
})
PACK_METADATA_PARTNER_NO_URL = json.dumps({
    "name": "test",
    "description": "test",
    "support": "partner",
    "currentVersion": "1.0.1",
    "author": "bar",
    "url": '',
    "email": PARTNER_EMAIL,
    "categories": [
        "Data Enrichment & Threat Intelligence"
    ],
    "tags": [],
    "useCases": [],
    "keywords": []
})
PACK_METADATA_XSOAR = json.dumps({
    "name": "test",
    "description": "test",
    "support": "xsoar",
    "currentVersion": "1.0.0",
    "author": "Cortex XSOAR",
    "url": "https://www.paloaltonetworks.com/cortex",
    "email": "",
    "categories": [
        "Endpoint"
    ],
    "tags": [],
    "useCases": [],
    "keywords": []
})

PACK_METADATA_COMMUNITY = json.dumps({
    "name": "test",
    "description": "test",
    "support": "community",
    "currentVersion": "1.0.0",
    "author": "Community Contributor",
    "url": "",
    "email": "",
    "categories": [
        "Endpoint"
    ],
    "tags": [],
    "useCases": [],
    "keywords": []
})

PARTNER_UNIFY = {
    'script': {},
    'type': 'python',
    'image': 'image',
    'detaileddescription': 'test details',
    'display': 'test'
}
PARTNER_UNIFY_NO_EMAIL = PARTNER_UNIFY.copy()
PARTNER_UNIFY_NO_URL = PARTNER_UNIFY.copy()
XSOAR_UNIFY = PARTNER_UNIFY.copy()
COMMUNITY_UNIFY = PARTNER_UNIFY.copy()
PARTNER_UNIFY_EMAIL_LIST = PARTNER_UNIFY.copy()

INTEGRATION_YAML = {'display': 'test', 'script': {'type': 'python'}}

PARTNER_DISPLAY_NAME = 'test (Partner Contribution)'
COMMUNITY_DISPLAY_NAME = 'test (Community Contribution)'
PARTNER_DETAILEDDESCRIPTION = '### This is a partner contributed integration' \
                              f'\nFor all questions and enhancement requests please contact the partner directly:' \
                              f'\n**Email** - [mailto](mailto:{PARTNER_EMAIL})\n**URL** - [{PARTNER_URL}]({PARTNER_URL})\n***\ntest details'
PARTNER_DETAILEDDESCRIPTION_NO_EMAIL = '### This is a partner contributed integration' \
                                       f'\nFor all questions and enhancement requests please contact the partner directly:' \
                                       f'\n**URL** - [{PARTNER_URL}]({PARTNER_URL})\n***\ntest details'
PARTNER_DETAILEDDESCRIPTION_NO_URL = '### This is a partner contributed integration' \
                                     f'\nFor all questions and enhancement requests please contact the partner directly:' \
                                     f'\n**Email** - [mailto](mailto:{PARTNER_EMAIL})\n***\ntest details'


def test_unify_partner_contributed_pack(mocker, repo):
    """
    Given
        - Partner contributed pack with email and url in the support details.
    When
        - Running unify on it.
    Then
        - Ensure unify create unified file with partner support notes.
    """
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration', 'bla', INTEGRATION_YAML)
    pack.pack_metadata.write_json(PACK_METADATA_PARTNER)
    mocker.patch.object(YmlUnifier, 'insert_script_to_yml', return_value=(PARTNER_UNIFY, ''))
    mocker.patch.object(YmlUnifier, 'insert_image_to_yml', return_value=(PARTNER_UNIFY, ''))
    mocker.patch.object(YmlUnifier, 'insert_description_to_yml', return_value=(PARTNER_UNIFY, ''))
    mocker.patch.object(YmlUnifier, 'get_data', return_value=(PACK_METADATA_PARTNER, pack.pack_metadata.path))

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [UNIFY_CMD, '-i', integration.path, '-o', integration.path], catch_exceptions=True)
    # Verifying unified process
    assert 'Merging package:' in result.stdout
    assert 'Created unified yml:' in result.stdout
    # Verifying the unified file data
    assert PARTNER_UNIFY["display"] == PARTNER_DISPLAY_NAME
    assert '#### Integration Author:' in PARTNER_UNIFY["detaileddescription"]
    assert 'Email' in PARTNER_UNIFY["detaileddescription"]
    assert 'URL' in PARTNER_UNIFY["detaileddescription"]


def test_unify_partner_contributed_pack_no_email(mocker, repo):
    """
    Given
        - Partner contributed pack with url and without email in the support details.
    When
        - Running unify on it.
    Then
        - Ensure unify create unified file with partner support notes.
    """
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration', 'bla', INTEGRATION_YAML)
    pack.pack_metadata.write_json(PACK_METADATA_PARTNER_NO_EMAIL)
    mocker.patch.object(YmlUnifier, 'insert_script_to_yml', return_value=(PARTNER_UNIFY_NO_EMAIL, ''))
    mocker.patch.object(YmlUnifier, 'insert_image_to_yml', return_value=(PARTNER_UNIFY_NO_EMAIL, ''))
    mocker.patch.object(YmlUnifier, 'insert_description_to_yml', return_value=(PARTNER_UNIFY_NO_EMAIL, ''))
    mocker.patch.object(YmlUnifier, 'get_data', return_value=(PACK_METADATA_PARTNER_NO_EMAIL, pack.pack_metadata.path))

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [UNIFY_CMD, '-i', integration.path, '-o', integration.path], catch_exceptions=True)
    # Verifying unified process
    assert 'Merging package:' in result.stdout
    assert 'Created unified yml:' in result.stdout
    # Verifying the unified file data
    assert PARTNER_UNIFY_NO_EMAIL["display"] == PARTNER_DISPLAY_NAME
    assert '#### Integration Author:' in PARTNER_UNIFY_NO_EMAIL["detaileddescription"]
    assert 'Email' not in PARTNER_UNIFY_NO_EMAIL["detaileddescription"]
    assert 'URL' in PARTNER_UNIFY_NO_EMAIL["detaileddescription"]


@pytest.mark.parametrize(argnames="pack_metadata",
                         argvalues=[PACK_METADATA_PARTNER_EMAIL_LIST, PACK_METADATA_STRINGS_EMAIL_LIST])
def test_unify_contributor_emails_list(mocker, repo, pack_metadata):
    """
    Given
        - Partner contributed pack with email list and url in the support details.
    When
        - Running unify on it.
    Then
        - Ensure unify create a unified file with partner support email list.
    """
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration', 'bla', INTEGRATION_YAML)
    pack.pack_metadata.write_json(pack_metadata)
    mocker.patch.object(YmlUnifier, 'insert_image_to_yml', return_value=(PARTNER_UNIFY_EMAIL_LIST, ''))
    mocker.patch.object(YmlUnifier, 'insert_description_to_yml', return_value=(PARTNER_UNIFY_EMAIL_LIST, ''))
    mocker.patch.object(YmlUnifier, 'get_data', return_value=(pack_metadata, pack.pack_metadata.path))

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        runner.invoke(main, [UNIFY_CMD, '-i', integration.path, '-o', integration.path], catch_exceptions=True)
    # Verifying the unified file data
    assert "**Email**: [support1@test.com]" in PARTNER_UNIFY_EMAIL_LIST["detaileddescription"]
    assert "**Email**: [support2@test.com]" in PARTNER_UNIFY_EMAIL_LIST["detaileddescription"]


def test_unify_partner_contributed_pack_no_url(mocker, repo):
    """
    Given
        - Partner contributed pack with email and without url in the support details
    When
        - Running unify on it.
    Then
        - Ensure unify create unified file with partner support notes.
    """
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration', 'bla', INTEGRATION_YAML)
    pack.pack_metadata.write_json(PACK_METADATA_PARTNER_NO_URL)
    mocker.patch.object(YmlUnifier, 'insert_script_to_yml', return_value=(PARTNER_UNIFY_NO_URL, ''))
    mocker.patch.object(YmlUnifier, 'insert_image_to_yml', return_value=(PARTNER_UNIFY_NO_URL, ''))
    mocker.patch.object(YmlUnifier, 'insert_description_to_yml', return_value=(PARTNER_UNIFY_NO_URL, ''))
    mocker.patch.object(YmlUnifier, 'get_data', return_value=(PACK_METADATA_PARTNER_NO_URL, pack.pack_metadata.path))

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [UNIFY_CMD, '-i', integration.path, '-o', integration.path], catch_exceptions=True)
    # Verifying unified process
    assert 'Merging package:' in result.stdout
    assert 'Created unified yml:' in result.stdout
    # Verifying the unified file data
    assert PARTNER_UNIFY_NO_URL["display"] == PARTNER_DISPLAY_NAME
    assert '#### Integration Author:' in PARTNER_UNIFY_NO_URL["detaileddescription"]
    assert 'Email' in PARTNER_UNIFY_NO_URL["detaileddescription"]
    assert 'URL' not in PARTNER_UNIFY_NO_URL["detaileddescription"]


def test_unify_not_partner_contributed_pack(mocker, repo):
    """
    Given
        - XSOAR supported - not a partner contribution
    When
        - Running unify on it.
    Then
        - Ensure unify create unified file without partner support notes.
    """
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration', 'bla', INTEGRATION_YAML)
    pack.pack_metadata.write_json(PACK_METADATA_XSOAR)
    mocker.patch.object(YmlUnifier, 'insert_script_to_yml', return_value=(XSOAR_UNIFY, ''))
    mocker.patch.object(YmlUnifier, 'insert_image_to_yml', return_value=(XSOAR_UNIFY, ''))
    mocker.patch.object(YmlUnifier, 'insert_description_to_yml', return_value=(XSOAR_UNIFY, ''))
    mocker.patch.object(YmlUnifier, 'get_data', return_value=(PACK_METADATA_XSOAR, pack.pack_metadata.path))

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [UNIFY_CMD, '-i', integration.path, '-o', integration.path], catch_exceptions=True)
    # Verifying unified process
    assert 'Merging package:' in result.stdout
    assert 'Created unified yml:' in result.stdout
    # Verifying the unified file data
    assert 'Partner' not in XSOAR_UNIFY["display"]
    assert 'partner' not in XSOAR_UNIFY["detaileddescription"]


def test_unify_community_contributed(mocker, repo):
    """
    Given
        - Community contribution.
    When
        - Running unify on it.
    Then
        - Ensure unify create unified file with community detailed description.
    """

    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration', 'bla', INTEGRATION_YAML)
    pack.pack_metadata.write_json(PACK_METADATA_COMMUNITY)
    mocker.patch.object(YmlUnifier, 'insert_script_to_yml', return_value=(COMMUNITY_UNIFY, ''))
    mocker.patch.object(YmlUnifier, 'insert_image_to_yml', return_value=(COMMUNITY_UNIFY, ''))
    mocker.patch.object(YmlUnifier, 'insert_description_to_yml', return_value=(COMMUNITY_UNIFY, ''))
    mocker.patch.object(YmlUnifier, 'get_data', return_value=(PACK_METADATA_COMMUNITY, pack.pack_metadata.path))

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [UNIFY_CMD, '-i', integration.path, '-o', integration.path], catch_exceptions=True)
    # Verifying unified process
    assert 'Merging package:' in result.stdout
    assert 'Created unified yml:' in result.stdout
    # Verifying the unified file data
    assert COMMUNITY_UNIFY["display"] == COMMUNITY_DISPLAY_NAME
    assert '#### Integration Author:' in COMMUNITY_UNIFY["detaileddescription"]
    assert 'No support or maintenance is provided by the author.' in COMMUNITY_UNIFY["detaileddescription"]


def test_invalid_path_to_unifier(repo):
    """
    Given:
    - Input path to integration YML for unify command.

    When:
    - Performing unify command.

    Then:
    - Ensure error message indicating path should be to a directory returned.

    """
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('integration', 'bla', INTEGRATION_YAML)
    integration.create_default_integration()

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [UNIFY_CMD, '-i', f'{integration.path}/integration.yml'])
    assert 'Unsupported input. Please provide either: ' \
           '1. a directory of an integration or a script. ' \
           '2. a path of a GenericModule file.' in result.stdout


def test_add_contributors_support(tmp_path):
    """
    Given:
        - partner integration which have (Partner Contribution) in the integration display name

    When:
        - Adding contribution support to display name

    Then:
        - Verify CONTRIBUTOR_DISPLAY_NAME is not added twice
    """
    unifier = YmlUnifier(str(tmp_path))
    unified_yml = {
        'display': 'Test Integration (Partner Contribution)',
        'commonfields': {'id': 'Test Integration'}
    }

    unifier.add_contributors_support(
        unified_yml=unified_yml,
        contributor_type='partner',
        contributor_email='',
        contributor_url='',
    )
    assert unified_yml["display"] == 'Test Integration (Partner Contribution)'
