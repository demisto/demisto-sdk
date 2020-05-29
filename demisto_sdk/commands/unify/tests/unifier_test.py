import base64
import copy
import os
import shutil

import pytest
import yaml
import yamlordereddictloader
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml
from mock import patch

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


def test_clean_python_code():
    from demisto_sdk.commands.unify.unifier import Unifier
    unifier = Unifier("test_files/VulnDB")
    script_code = "import demistomock as demistofrom CommonServerPython import *" \
                  "from CommonServerUserPython import *from __future__ import print_function"
    # Test remove_print_future is False
    script_code = unifier.clean_python_code(script_code, remove_print_future=False)
    assert script_code == "from __future__ import print_function"
    # Test remove_print_future is True
    script_code = unifier.clean_python_code(script_code)
    assert script_code == ""


def test_get_code_file():
    from demisto_sdk.commands.unify.unifier import Unifier
    # Test integration case
    unifier = Unifier(f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/")
    assert unifier.get_code_file(".py") == f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB.py"
    unifier = Unifier(f"{git_path()}/demisto_sdk/tests/test_files/Unifier/SampleNoPyFile")
    with pytest.raises(Exception):
        unifier.get_code_file(".py")
    # Test script case
    unifier = Unifier(f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/")
    assert unifier.get_code_file(".py") == f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/" \
                                           f"CalculateGeoDistance.py"


def test_get_script_or_integration_package_data():
    from demisto_sdk.commands.unify.unifier import Unifier
    unifier = Unifier(f"{git_path()}/demisto_sdk/tests/test_files/Unifier/SampleNoPyFile")
    with pytest.raises(Exception):
        unifier.get_script_or_integration_package_data()
    unifier = Unifier(f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance")
    with open(f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/CalculateGeoDistance.py", "r") as \
            code_file:
        code = code_file.read()
    yml_path, code_data = unifier.get_script_or_integration_package_data()
    assert yml_path == f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/CalculateGeoDistance.yml"
    assert code_data == code


def test_get_data():
    from demisto_sdk.commands.unify.unifier import Unifier
    with patch.object(Unifier, "__init__", lambda a, b, c, d, e: None):
        unifier = Unifier('', None, None, None)
        unifier.package_path = f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/"
        unifier.is_script_package = False
        with open(f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_image.png", "rb") as image_file:
            image = image_file.read()
        data, found_data_path = unifier.get_data("*png")
        assert data == image
        assert found_data_path == f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_image.png"
        unifier.is_script_package = True
        data, found_data_path = unifier.get_data("*png")
        assert data is None
        assert found_data_path is None


def test_insert_description_to_yml():
    from demisto_sdk.commands.unify.unifier import Unifier
    with patch.object(Unifier, "__init__", lambda a, b, c, d, e: None):
        unifier = Unifier('', None, None, None)
        unifier.package_path = f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/"
        unifier.dir_name = "Integrations"
        unifier.is_script_package = False
        with open(f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_description.md", "rb") as desc_file:
            desc_data = desc_file.read().decode("utf-8")
        yml_unified, found_data_path = unifier.insert_description_to_yml({}, {})

        assert found_data_path == f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/VulnDB_description.md"
        assert desc_data == yml_unified['detaileddescription']


def test_insert_image_to_yml():
    from demisto_sdk.commands.unify.unifier import Unifier
    with patch.object(Unifier, "__init__", lambda a, b, c, d, e: None):
        unifier = Unifier('', None, None, None)
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


def test_check_api_module_imports():
    from demisto_sdk.commands.unify.unifier import Unifier
    module_import, module_name = Unifier.check_api_module_imports(DUMMY_SCRIPT)

    assert module_import == 'from MicrosoftApiModule import *  # noqa: E402'
    assert module_name == 'MicrosoftApiModule'


@pytest.mark.parametrize('import_name', ['from MicrosoftApiModule import *  # noqa: E402',
                                         'from MicrosoftApiModule import *'])
def test_insert_module_code(mocker, import_name):
    from demisto_sdk.commands.unify.unifier import Unifier
    mocker.patch.object(Unifier, '_get_api_module_code', return_value=DUMMY_MODULE)
    module_name = 'MicrosoftApiModule'
    new_code = DUMMY_SCRIPT.replace(import_name, '\n### GENERATED CODE ###\n# This code was inserted in place of an API'
                                                 ' module.{}\n'.format(DUMMY_MODULE))

    code = Unifier.insert_module_code(DUMMY_SCRIPT, import_name, module_name)

    assert code == new_code


@pytest.mark.parametrize('package_path, dir_name, file_path', [
    (f"{git_path()}/demisto_sdk/tests/test_files/VulnDB/", "Integrations", f"{git_path()}/demisto_sdk/tests/test_files/"
                                                                           f"VulnDB/VulnDB"),
    (f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/", "Scripts",
     f"{git_path()}/demisto_sdk/tests/test_files/CalculateGeoDistance/CalculateGeoDistance")])
def test_insert_script_to_yml(package_path, dir_name, file_path):
    from demisto_sdk.commands.unify.unifier import Unifier
    with patch.object(Unifier, "__init__", lambda a, b, c, d, e: None):
        unifier = Unifier("", None, None, None)
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
    from demisto_sdk.commands.unify.unifier import Unifier
    with patch.object(Unifier, "__init__", lambda a, b, c, d, e: None):
        unifier = Unifier("", None, None, None)
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
    def setup(self):
        self.test_dir_path = os.path.join('tests', 'test_files', 'Unifier', 'Testing')
        os.makedirs(self.test_dir_path)
        self.package_name = 'SampleIntegPackage'
        self.export_dir_path = os.path.join(self.test_dir_path, self.package_name)
        self.expected_yml_path = os.path.join(self.test_dir_path, 'integration-SampleIntegPackage.yml')

    def teardown(self):
        if self.test_dir_path:
            shutil.rmtree(self.test_dir_path)

    def test_unify_integration(self):
        """
        sanity test of merge_script_package_to_yml of integration
        """
        from demisto_sdk.commands.unify.unifier import Unifier

        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml='demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage.yml',
            script_code=TEST_VALID_CODE,
            detailed_description=TEST_VALID_DETAILED_DESCRIPTION,
            image_file='demisto_sdk/tests/test_files/Unifier/SampleIntegPackage/SampleIntegPackage_image.png',
        )

        unifier = Unifier(input=self.export_dir_path, output=self.test_dir_path)
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
        from demisto_sdk.commands.unify.unifier import Unifier
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

        unifier = Unifier(self.export_dir_path, output=self.test_dir_path)
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
        from demisto_sdk.commands.unify.unifier import Unifier
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

        unifier = Unifier(self.export_dir_path, output=self.test_dir_path)
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
        from demisto_sdk.commands.unify.unifier import Unifier
        input_path_integration = TESTS_DIR + '/test_files/Packs/DummyPack/Integrations/UploadTest'
        unifier = Unifier(input_path_integration)
        yml_files = unifier.merge_script_package_to_yml()
        export_yml_path = yml_files[0]
        expected_yml_path = TESTS_DIR + '/test_files/Packs/DummyPack/Integrations/UploadTest/integration-UploadTest.yml'

        assert export_yml_path == expected_yml_path
        os.remove(expected_yml_path)


class TestMergeScriptPackageToYMLScript:
    def setup(self):
        self.test_dir_path = os.path.join('tests', 'test_files', 'Unifier', 'Testing')
        os.makedirs(self.test_dir_path)
        self.package_name = 'SampleScriptPackage'
        self.export_dir_path = os.path.join(self.test_dir_path, self.package_name)
        self.expected_yml_path = os.path.join(self.test_dir_path, 'script-SampleScriptPackage.yml')

    def teardown(self):
        if self.test_dir_path:
            shutil.rmtree(self.test_dir_path)

    def test_unify_script(self):
        """
        sanity test of merge_script_package_to_yml of script
        """
        from demisto_sdk.commands.unify.unifier import Unifier

        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml='demisto_sdk/tests/test_files/Unifier/SampleScriptPackage/SampleScriptPackage.yml',
            script_code=TEST_VALID_CODE,
        )

        unifier = Unifier(input=self.export_dir_path, output=self.test_dir_path)
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
        from demisto_sdk.commands.unify.unifier import Unifier

        create_test_package(
            test_dir=self.test_dir_path,
            package_name=self.package_name,
            base_yml='demisto_sdk/tests/test_files/Unifier/SampleScriptPackage/SampleScriptPackageDocker45.yml',
            script_code=TEST_VALID_CODE,
        )

        unifier = Unifier(input=self.export_dir_path, output=self.test_dir_path)
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

        from demisto_sdk.commands.unify.unifier import Unifier
        input_path_script = TESTS_DIR + '/test_files/Packs/DummyPack/Scripts/DummyScript'
        unifier = Unifier(input_path_script)
        yml_files = unifier.merge_script_package_to_yml()
        export_yml_path = yml_files[0]
        expected_yml_path = TESTS_DIR + '/test_files/Packs/DummyPack/Scripts/DummyScript/script-DummyScript.yml'

        assert export_yml_path == expected_yml_path
        os.remove(expected_yml_path)
