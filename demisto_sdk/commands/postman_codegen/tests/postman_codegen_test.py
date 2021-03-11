import json
import os
from pathlib import Path

import yaml
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.generate_integration.code_generator import (
    IntegrationGeneratorCommand, IntegrationGeneratorConfig,
    IntegrationGeneratorOutput, json_body_to_code)
from demisto_sdk.commands.postman_codegen.postman_codegen import (
    create_body_format, postman_to_autogen_configuration)

expected_command_function = '''def get_pet_by_id_command(client, args):
    petId = args.get('petId', None)

    response = client.get_pet_by_id_request(petId)
    command_results = CommandResults(
        outputs_prefix='TestSwagger.Pet',
        outputs_key_field='id',
        outputs=response,
        raw_response=response
    )

    return command_results

'''

expected_request_function = ('\n'
                             '    def get_pet_by_id_request(self, petId):\n'
                             '\n'
                             '        headers = self._headers\n'
                             '\n'
                             '        response = self._http_request(\'get\', f\'pet/{petId}\', headers=headers)\n'
                             '\n'
                             '        return response\n'
                             '\n')


def test_create_body_format():
    request_body = {
        "key1": "val1",
        "key2": {
            "key3": "val3"
        },
        "key4": [
            {
                "key5": "val5"
            },
            {
                "key5": "val51"
            },
        ],
        "key7": [
            "a",
            "b",
            "c"
        ]
    }
    body_format = create_body_format(request_body)

    assert body_format == {
        "key1": "{key1}",
        "key2": {
            "key3": "{key3}"
        },
        "key4": [
            {
                "key5": "{key5}"
            }
        ],
        "key7": "{key7}"
    }


def test_create_body_format_list_of_dicts():
    request_body = [
        {
            "key1": "val1"
        },
        {
            "key1": "val11"
        }
    ]

    body_format = create_body_format(request_body)

    assert body_format == [
        {
            "key1": "{key1}"
        }
    ]


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


class TestPostmanCodeGen:
    test_files_path = os.path.join(git_path(), 'demisto_sdk', 'commands', 'postman_codegen', 'resources')
    test_integration_dir = os.path.join(test_files_path, 'VirusTotalTest')
    postman_collection_path = os.path.join(test_files_path, 'VirusTotal.postman_collection.json')

    def test_config_generated_successfully(self, mocker):
        from demisto_sdk.commands.common.hook_validations.docker import \
            DockerImageValidator

        mocker.patch.object(DockerImageValidator, 'get_docker_image_latest_tag_request', return_value='3.8.6.12176')

        autogen_config = postman_to_autogen_configuration(
            collection_path=self.postman_collection_path,
            name='VirusTotal Test',
            command_prefix='vt-test',
            context_path_prefix='VirusTotalTest'
        )

        with open(os.path.join(self.test_files_path, 'VirusTotal-autogen-config.json'), 'r') as config_file:
            expected_config = json.load(config_file)

        with open(os.path.join(self.test_files_path, 'VT-config-result.json'), 'w') as g:
            g.write(json.dumps(autogen_config, default=lambda o: o.__dict__, indent=4))

        assert expected_config == autogen_config.to_dict()

    def test_py_code_generated_from_config(self, mocker, tmpdir):
        from demisto_sdk.commands.common.hook_validations.docker import \
            DockerImageValidator

        mocker.patch.object(DockerImageValidator, 'get_docker_image_latest_tag_request', return_value='3.8.6.12176')

        autogen_config = None
        with open(os.path.join(self.test_files_path, 'VT-config-result.json'), mode='r') as f:
            config_dict = json.load(f)
            config_dict['fix_code'] = True
            autogen_config: IntegrationGeneratorConfig = IntegrationGeneratorConfig(**config_dict)

        code = autogen_config.generate_integration_python_code()
        with open(os.path.join(self.test_files_path, 'VT-actual-code.py'), 'w') as g:
            g.write(code)

        with open(os.path.join(self.test_integration_dir, 'VirusTotalTest.py'), mode='r') as f:
            expected_code = f.read()

            assert expected_code == code

    def test_yml_generated_from_config(self, mocker):
        """
        Scenario: Generating an integration from generated config file

        Given
        - generated xsoar integration config file for VirusTotal Test

        When
        - generating integration yml file

        Then
        - ensure it generates the yml successfully and the yml is the exact as expected yml from resources folder
       """
        import yaml

        from demisto_sdk.commands.common.hook_validations.docker import \
            DockerImageValidator

        mocker.patch.object(DockerImageValidator, 'get_docker_image_latest_tag_request', return_value='3.8.6.12176')

        autogen_config = None
        with open(os.path.join(self.test_files_path, 'VT-config-result.json'), mode='r') as f:
            config_dict = json.load(f)
            config_dict['fix_code'] = True
            autogen_config: IntegrationGeneratorConfig = IntegrationGeneratorConfig(**config_dict)

        yaml_obj = autogen_config.generate_integration_yml().to_yaml()
        with open(os.path.join(self.test_integration_dir, 'VirusTotalTest.yml'), mode='r') as f:
            expected_yml = f.read()

        actual_yml = yaml.dump(yaml_obj)
        with open(os.path.join(self.test_integration_dir, 'actual.yml'), mode='w') as f:
            f.write(actual_yml)
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

        autogen_config = None
        with open(os.path.join(self.test_files_path, 'VT-config-result.json'), mode='r') as f:
            config_dict = json.load(f)
            config_dict['fix_code'] = True
            autogen_config: IntegrationGeneratorConfig = IntegrationGeneratorConfig(**config_dict)

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
        with open(os.path.join(self.test_files_path, 'VT-config-result.json'), mode='r') as f:
            config_dict = json.load(f)
            config_dict['fix_code'] = True
            autogen_config: IntegrationGeneratorConfig = IntegrationGeneratorConfig(**config_dict)

        autogen_config.generate_integration_package(
            output_dir=tmpdir,
            is_unified=True
        )

        assert os.path.isfile(Path(tmpdir, 'integration-VirusTotalTest.yml'))
        with open(Path(tmpdir, 'integration-VirusTotalTest.yml'), mode='r') as f:
            actual_unified_yml = f.read()
            assert actual_unified_yml.find('class Client(BaseClient):')
            assert actual_unified_yml.find('- display: Trust any certificate')

    def test_command_prefix(self):
        """
        Given
        - postman collection with name Virus Total

        When
        - generating config file

        Then
        - ensure command_prefix is virustotal-

        """
        autogen_config = postman_to_autogen_configuration(
            collection_path=self.postman_collection_path,
            command_prefix=None,

            name=None,
            context_path_prefix=None,
            category=None
        )

        assert autogen_config.command_prefix == 'virustotal'

    def test_context_output_path(self):
        """
        Given
        - postman collection with name Virus Total

        When
        - generating config file

        Then
        - ensure context_output_path of the whole integration is VirusTotal
        """
        autogen_config = postman_to_autogen_configuration(
            collection_path=self.postman_collection_path,
            context_path_prefix=None,

            command_prefix=None,
            name=None,
            category=None
        )

        assert autogen_config.context_path == 'VirusTotal'

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
        with open(os.path.join(self.test_files_path, 'VT-config-result.json'), mode='r') as f:
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
        integration_yml_str = yaml.dump(integration_yml.to_yaml())

        assert "outputs=response.get('scans')" in integration_code
        assert 'contextPath: VirusTotalTest.TestScan.scans.field1' in integration_yml_str
        assert 'contextPath: VirusTotalTest.TestScan.total_count' in integration_yml_str

    def test_url_contains_args(self, tmp_path):
        """
        Given
        - postman collection
        - with request Test Report which has variable {{foo}} in the url like: {{url}}/vtapi/v2/test/{{foo}}?resource=https://www.cobaltstrike.com/

        When
        - generating config file

        Then
        - integration code, the command test-report will contain foo argument passed to the url
        - integration yml, the command test-report will contain foo arg
        """
        path = tmp_path / 'test-collection.json'
        _testutil_create_postman_collection(dest_path=path, with_request={
            "name": "Test Report",
            "request": {
                "method": "GET",
                "header": [],
                "url": {
                    "raw": "{{url}}/vtapi/v2/test/{{foo}}?resource=https://www.cobaltstrike.com/",
                    "host": [
                        "{{url}}"
                    ],
                    "path": [
                        "vtapi",
                        "v2",
                        "test",
                        "{{foo}}"
                    ],
                    "query": [
                        {
                            "key": "resource",
                            "value": "https://www.cobaltstrike.com/"
                        }
                    ]
                },
                "description": "Test Report description"
            }
        })

        config = postman_to_autogen_configuration(
            collection_path=path,
            name='VirusTotal',
            context_path_prefix=None,
            command_prefix=None
        )

        integration_code = config.generate_integration_python_code()
        integration_obj = config.generate_integration_yml()
        integration_yml = yaml.dump(integration_obj.to_yaml())

        with open(Path(self.test_integration_dir, 'actual.py'), mode='w') as f:
            f.write(integration_code)

        with open(Path(self.test_integration_dir, 'actual.yml'), mode='w') as f:
            f.write(integration_yml)

        assert "foo = str(args.get('foo', ''))" in integration_code
        assert "def test_report_request(self, foo, resource):" in integration_code
        assert "'GET', f'vtapi/v2/test/{foo}', params=params, headers=headers)" in integration_code

        assert 'name: foo' in integration_yml

    def test_apikey_passed_as_header(self, tmpdir):
        """
        Scenario: sometimes the auth method will not be defined under auth section, but as plain header Authorization

        Given
        - postman collection
        - with no auth defined
        - with request with headers:
            - "Authorization" header with value "SWSS {{apikey}}"
            - and other typical headers like Content-Type and Accept

        When
        - generating config file

        Then
        - config file should contain auth
        """
        path = Path(tmpdir, 'config.json')
        _testutil_create_postman_collection(
            dest_path=path,
            with_request={
                "name": "Test Report",
                "request": {
                    "method": "GET",
                    "header": [
                        {
                            "key": "Accept",
                            "value": "application/json"
                        },
                        {
                            "key": "Content-Type",
                            "value": "application/json"
                        },
                        {
                            "key": "Authorization",
                            "value": "SSWS {{apikey}}"
                        }
                    ],
                    "url": {
                        "raw": "{{url}}/test/",
                        "host": [
                            "{{url}}"
                        ],
                        "path": [
                            "test",
                        ]
                    },
                    "description": "Test Report description"
                }
            },
            no_auth=True
        )

        config = postman_to_autogen_configuration(
            collection_path=path,
            name=None,
            command_prefix=None,
            context_path_prefix=None,
            category=None
        )

        with open(Path(self.test_integration_dir, 'actual-config.json'), mode='w') as f:
            json.dump(config.to_dict(), f, indent=4)

        assert _testutil_get_param(config, 'apikey') is not None
        command = _testutil_get_command(config, 'test-report')
        assert command.headers == [
            {
                "Accept": "application/json"
            },
            {
                "Content-Type": "application/json"
            }
        ]
        assert config.auth == {
            "type": "apikey",
            "apikey": [
                {
                    "key": "format",
                    "value": "f'SSWS {params[\"api_key\"]}'",
                    "type": "string"
                },
                {
                    "key": "in",
                    "value": "header",
                    "type": "string"
                },
                {
                    "key": "key",
                    "value": "Authorization",
                    "type": "string"
                }
            ]
        }

        integration_code = config.generate_integration_python_code()

        with open(Path(self.test_integration_dir, 'actual.py'), mode='w') as f:
            f.write(integration_code)

        assert "headers['Authorization'] = f'SSWS {params[\"api_key\"]}'" in integration_code

    def test_post_body_to_arguments(self, tmpdir):
        """
        If POST request requires data passed in the body, then command arguments should construct that data

        Given
        - postman collection
        - with POST request "test-create-group"
        - "test-create" requires data of the following structure
        {
            "test_name": "some name",
            "test_id": "some id",
            "test_filter": {
                "test_key": "this is nested object"
            }
        }

        When
        - creating config file

        Then
        - test-create command should contain arguments of "test_name" "test_id" "test_filter"

        When
        - generating code from the config file

        Then
        - "name", "id" and "filter" must be passed as request body
        - "name", "id" and "filter" should be arguments of "test-create-group" command in yml
        """
        path = Path(tmpdir, 'config.json')
        _testutil_create_postman_collection(
            dest_path=path,
            with_request={
                "name": "Test Create Group",
                "request": {
                    "method": "POST",
                    "header": [
                        {
                            "key": "Accept",
                            "value": "application/json"
                        },
                        {
                            "key": "Content-Type",
                            "value": "application/json"
                        },
                        {
                            "key": "Authorization",
                            "value": "SSWS {{apikey}}"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": """{"test_name":"some name","test_id":"some id","test_filter":{"test_key":"this is nested object"}}"""
                    },
                    "url": {
                        "raw": "{{url}}/api/v1/groups",
                        "host": [
                            "{{url}}"
                        ],
                        "path": [
                            "api",
                            "v1",
                            "groups"
                        ]
                    }
                },
                "response": []
            }
        )

        config = postman_to_autogen_configuration(
            collection_path=path,
            name=None,
            command_prefix=None,
            context_path_prefix=None,
            category=None
        )

        with open(Path(self.test_integration_dir, 'actual-config.json'), mode='w') as f:
            json.dump(config.to_dict(), f, indent=4)

        command = _testutil_get_command(config, 'test-create-group')
        assert len(command.arguments) == 3
        assert command.arguments[0].name == 'test_name'
        assert command.arguments[0].in_ == 'body'
        assert not command.arguments[0].in_object

        assert command.arguments[1].name == 'test_id'
        assert command.arguments[1].in_ == 'body'
        assert not command.arguments[1].in_object

        assert command.arguments[2].name == 'test_key'
        assert command.arguments[2].in_ == 'body'
        assert command.arguments[2].in_object == ['test_filter']

        integration_code = config.generate_integration_python_code()
        integration_obj = config.generate_integration_yml()
        integration_yml = yaml.dump(integration_obj.to_yaml())

        with open(Path(self.test_integration_dir, 'actual.py'), mode='w') as f:
            f.write(integration_code)

        assert 'def test_create_group_request(self, test_name, test_id, test_key):' in integration_code
        assert 'data={"test_filter": {"test_key": test_key}, "test_id": test_id, "test_name": test_name}' in integration_code
        assert 'response = self._http_request(\'POST\', \'api/v1/groups\', params=params, json_data=data, headers=headers)' in integration_code

        assert "name: test_id" in integration_yml
        assert "name: test_name" in integration_yml
        assert "name: test_key" in integration_yml

    def test_download_file(self):
        """
        Given
        - postman collection
        - with file-download request which has response with "_postman_previewlanguage": "raw"

        When
        - generating config file

        Then
        - ensure file-download request has "return_file": true

        When
        - generating integration

        Then
        - integration code, file_download_command should call fileResult function
        - integration yml, file-download should return File standard context outputs
        """
        pass


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
        headers={},
        unique_key='',
        upload_file=False,
        returns_file=False,
        returns_entry_file=False
    )


def _testutil_create_postman_collection(dest_path, with_request: dict = None, no_auth: bool = False):
    default_collection_path = os.path.join(git_path(), 'demisto_sdk', 'commands', 'postman_codegen', 'resources', 'VirusTotal.postman_collection.json')
    with open(default_collection_path, mode='r') as f:
        collection = json.load(f)

    if with_request:
        collection['item'].append(with_request)

    if no_auth:
        del collection['auth']

    with open(dest_path, mode='w') as f:
        json.dump(collection, f)


def _testutil_get_param(config: IntegrationGeneratorConfig, param_name: str):
    if config.params is None:
        return None

    for param in config.params:
        if param.name == param_name:
            return param

    return None


def _testutil_get_command(config: IntegrationGeneratorConfig, command_name: str):
    if config.commands is None:
        return None

    for command in config.commands:
        if command.name == command_name:
            return command

    return None
