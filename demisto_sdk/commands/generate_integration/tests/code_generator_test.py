import json
import os
from pathlib import Path

import yaml
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.generate_integration.code_generator import (
    IntegrationGeneratorCommand, IntegrationGeneratorConfig,
    IntegrationGeneratorOutput, json_body_to_code)


def test_json_body_to_code():
    """
    Given:
    - request with body in config file
    {
        "test_id": "{test_id}",
        "test_name": "{test_name}",
        "test_filter": {
            "test_key": "{test_key}",
            "test_const": "CONST VALUE"
        }
    }

    When:
    - when converting json body request to code

    Then:
    - ensure {var_name} converted to variables without {} -> "{test_id}" -> test_id
    - data={
        "test_id": test_id,
        "test_name": test_name,
        "test_filter": {
            "test_key": test_key,
            "test_const": "CONST VALUE"
        }
    }
    """
    request_body = {
        "test_id": "{test_id}",
        "test_name": "{test_name}",
        "test_filter": {
            "test_key": "{test_key}",
            "test_const": "CONST VALUE"
        }
    }

    body_code = json_body_to_code(request_body)
    assert body_code == 'data={"test_filter": {"test_const": "CONST VALUE", "test_key": test_key}, "test_id": test_id, "test_name": test_name}'


class TestCodeGenerator:
    test_files_path = os.path.join(git_path(), 'demisto_sdk', 'commands', 'generate_integration', 'tests', 'test_files')
    test_integration_dir = os.path.join(test_files_path, 'VirusTotalTest')
    autogen_config_path = os.path.join(test_files_path, 'VirusTotal-autogen-config.json')

    def test_py_code_generated_from_config(self, mocker, tmpdir):
        """
        This test will fail for every change in the generated python code!!

        This is general happy path test, the purpose of this test is not to test something specifically
        but to make sure if something changed in generated python file, this test will fail because it is not
        identical with the actual result.

        If this test fails, validate that the reason for the failure is valid and then
        update the test python file under test_files folder.

        Given
        - code genereator config file, which was generated for VirusTotal api (4 commands)

        When
        - generating code from it

        Then
        - ensure code is generated
        - esnrue the code is identical to what is stored under test_files folder
        """
        from demisto_sdk.commands.common.hook_validations.docker import \
            DockerImageValidator

        mocker.patch.object(DockerImageValidator, 'get_docker_image_latest_tag_request', return_value='3.8.6.12176')

        autogen_config = None
        with open(self.autogen_config_path, mode='r') as f:
            config_dict = json.load(f)
            config_dict['fix_code'] = True
            autogen_config = IntegrationGeneratorConfig(**config_dict)

        code = autogen_config.generate_integration_python_code()

        with open(os.path.join(self.test_integration_dir, 'VirusTotalTest.py'), mode='r') as f:
            expected_code = f.read()

            assert expected_code == code

    def test_yml_generated_from_config(self, mocker):
        """
        This test will fail for every change in the generated integration yml file!!

        This is general happy path test, the purpose of this test is not to test something specifically
        but to make sure if something changed in generated yml file, this test will fail because it is not
        identical with the actual result.

        If this test fails, validate that the reason for the failure is valid and then
        update the test python file under test_files folder.

        Given
        - generated xsoar integration config file for VirusTotal Test

        When
        - generating integration yml file

        Then
        - ensure it generates the yml successfully and the yml is the exact as expected yml from test_files folder
       """
        import yaml

        from demisto_sdk.commands.common.hook_validations.docker import \
            DockerImageValidator

        mocker.patch.object(DockerImageValidator, 'get_docker_image_latest_tag_request', return_value='3.8.6.12176')

        with open(self.autogen_config_path, mode='r') as f:
            config_dict = json.load(f)
            config_dict['fix_code'] = True
            autogen_config = IntegrationGeneratorConfig(**config_dict)

        yaml_obj = autogen_config.generate_integration_yml().to_dict()
        with open(os.path.join(self.test_integration_dir, 'VirusTotalTest.yml'), mode='r') as f:
            expected_yml = f.read()

        actual_yml = yaml.dump(yaml_obj)
        assert expected_yml == actual_yml

    def test_generate_integration_package(self, tmpdir, mocker):
        """
        Given
        - generated xsoar integration config file for VirusTotal Test

        When
        - generating xsoar integration package from config file

        Then
        - ensure VirusTotalTest dir created
        - ensure VirusTotalTest dir contains VirusTotalTest.py
        - ensure VirusTotalTest dir contains VirusTotalTest.yml
        """
        from demisto_sdk.commands.common.hook_validations.docker import \
            DockerImageValidator

        mocker.patch.object(DockerImageValidator, 'get_docker_image_latest_tag_request', return_value='3.8.6.12176')

        with open(self.autogen_config_path, mode='r') as f:
            config_dict = json.load(f)
            config_dict['fix_code'] = True
            autogen_config = IntegrationGeneratorConfig(**config_dict)

        autogen_config.generate_integration_package(
            output_dir=tmpdir
        )

        assert os.path.isdir(Path(tmpdir, 'VirusTotalTest'))
        assert os.path.isfile(Path(tmpdir, 'VirusTotalTest', 'VirusTotalTest.py'))
        assert os.path.isfile(Path(tmpdir, 'VirusTotalTest', 'VirusTotalTest.yml'))

    def test_generate_unified_integration_yml(self, tmpdir, mocker):
        """
        Given
        - generated xsoar integration config file for VirusTotal Test

        When
        - generating xsoar integration unified yml from config file

        Then
        - ensure integration-VirusTotalTest.yml exists
        - ensure the unified file contains the script
        """
        from demisto_sdk.commands.common.hook_validations.docker import \
            DockerImageValidator

        mocker.patch.object(DockerImageValidator, 'get_docker_image_latest_tag_request', return_value='3.8.6.12176')

        autogen_config = None
        with open(self.autogen_config_path, mode='r') as f:
            config_dict = json.load(f)
            config_dict['fix_code'] = True
            autogen_config = IntegrationGeneratorConfig(**config_dict)

        assert autogen_config
        autogen_config.generate_integration_package(
            output_dir=tmpdir,
            is_unified=True
        )

        assert os.path.isfile(Path(tmpdir, 'integration-VirusTotalTest.yml'))
        with open(Path(tmpdir, 'integration-VirusTotalTest.yml'), mode='r') as f:
            actual_unified_yml = f.read()
            assert actual_unified_yml.find('class Client(BaseClient):')
            assert actual_unified_yml.find('- display: Trust any certificate')
            assert not actual_unified_yml.find('name: RESOURCE')

    def test_query_response_root_object(self):
        """
        Given
        - integration config file
        - with command test-scan
        - with root object "scans"

        When
        - generating the integration py and yml files

        Then
        - ensure in the code we return response.get('scans')
        - ensure in yml, we generate outputs for scans object, and not to the whole response
        """
        with open(os.path.join(self.test_files_path, 'VirusTotal-autogen-config.json'), mode='r') as f:
            config_dict = json.load(f)

        config = IntegrationGeneratorConfig(**config_dict)
        test_command = _testutil_create_command(name='test-scan', root_object='scans', context_path='TestScan', outputs=[
            IntegrationGeneratorOutput(
                name='total_count',
                description='',
                type_='Number'
            ),
            IntegrationGeneratorOutput(
                name='scans.field1',
                description='',
                type_='String'
            ),
        ])
        config.commands.append(test_command)

        integration_code = config.generate_integration_python_code()
        integration_yml = config.generate_integration_yml()
        integration_yml_str = yaml.dump(integration_yml.to_dict())

        assert "outputs=response.get('scans')" in integration_code
        assert 'contextPath: VirusTotalTest.TestScan.scans.field1' in integration_yml_str
        assert 'contextPath: VirusTotalTest.TestScan.total_count' in integration_yml_str


def _testutil_create_command(name, root_object=None, context_path=None, url_path=None, outputs=None):
    if url_path is None:
        url_path = '/test'

    return IntegrationGeneratorCommand(
        name=name,
        http_method='GET',
        url_path=url_path,
        root_object=root_object,
        context_path=context_path,
        description='',
        arguments=[],
        outputs=outputs,
        headers=[],
        unique_key='',
        upload_file=False,
        returns_file=False,
        returns_entry_file=False
    )
