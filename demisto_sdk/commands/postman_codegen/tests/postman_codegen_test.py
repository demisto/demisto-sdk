import json
import os
from pathlib import Path
from typing import Optional

import pytest
import yaml
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.generate_integration.code_generator import \
    IntegrationGeneratorConfig
from demisto_sdk.commands.postman_codegen.postman_codegen import (
    create_body_format, flatten_collections, postman_to_autogen_configuration)


class TestPostmanHelpers:
    def test_create_body_format(self):
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

    def test_create_body_format_list_of_dicts(self):
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

    @pytest.mark.parametrize('collection, outputs', [
        ([], []),
        ([[], []], []),
        ([{}, [], [{}]], [{}, {}]),
        ([{'item': [{}]}, [], [{}]], [{}, {}])
    ])
    def test_flatten_collections(self, collection: list, outputs: list):
        assert flatten_collections(collection) == outputs


class TestPostmanCodeGen:
    test_files_path = os.path.join(git_path(), 'demisto_sdk', 'commands', 'postman_codegen', 'tests', 'test_files')
    postman_collection_stream = None
    autogen_config_stream = None
    postman_collection: dict
    autogen_config: dict

    @classmethod
    def setup_class(cls):
        collection_path = os.path.join(cls.test_files_path, 'VirusTotal.postman_collection.json')
        autogen_config_path = os.path.join(cls.test_files_path, 'VirusTotal-autogen-config.json')
        with open(collection_path) as f:
            cls.postman_collection = json.load(f)

        with open(autogen_config_path) as f:
            cls.autogen_config = json.load(f)

        cls.postman_collection_stream = open(collection_path)
        cls.autogen_config_stream = open(autogen_config_path)

    @classmethod
    def teardown_class(cls):
        cls.postman_collection_stream.close()
        cls.autogen_config_stream.close()

    @classmethod
    @pytest.fixture(autouse=True)
    def function_setup(cls):
        """
        Cleaning the content repo before every function
        """
        cls.postman_collection_stream.seek(0)
        cls.autogen_config_stream.seek(0)

    def test_config_generated_successfully(self, mocker):
        """
        This is general happy path test, the purpose of this test is not to test something specifically
        but to make sure if something changed in config file schema or broken, this test will fail because it is not
        identical with the actual result.
        If this test fails, validate that the reason for the failure is valid (like on purpose schema update) and then
        update the test file under resources folder.

        Given
        - Postman collection v2.1 of 4 Virus Total API commands

        When
        - generating config file from the postman collection

        Then
        - ensure the config file is generated
        - the config file should be identical to the one we have under resources folder
        """
        from demisto_sdk.commands.common.hook_validations.docker import \
            DockerImageValidator

        mocker.patch.object(DockerImageValidator, 'get_docker_image_latest_tag_request', return_value='3.8.6.12176')

        autogen_config = postman_to_autogen_configuration(
            collection=self.postman_collection,
            name='VirusTotal Test',
            command_prefix='vt-test',
            context_path_prefix='VirusTotalTest'
        )

        expected_config = json.load(self.autogen_config_stream)

        assert expected_config == autogen_config.to_dict()

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
            collection=self.postman_collection,
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
            collection=self.postman_collection,
            context_path_prefix=None,

            command_prefix=None,
            name=None,
            category=None
        )

        assert autogen_config.context_path == 'VirusTotal'

    def test_url_contains_args(self, tmp_path):
        """
        Given
        - postman collection
        - with request Test Report which has variable {{foo}} in the url like:
        {{url}}/vtapi/v2/:virus_name/test/{{foo}}?resource=https://www.cobaltstrike.com/

        When
        - generating config file

        Then
        - integration code, the command test-report will contain foo argument passed to the url
        - integration yml, the command test-report will contain foo arg
        - integration yml, the command test-report will contain virus_name arg.
        """
        path = tmp_path / 'test-collection.json'
        _testutil_create_postman_collection(dest_path=path, with_request={
            "name": "Test Report",
            "request": {
                "method": "GET",
                "header": [],
                "url": {
                    "raw": "{{url}}/vtapi/v2/:virus_name/test/{{foo}}?resource=https://www.cobaltstrike.com/",
                    "host": [
                        "{{url}}"
                    ],
                    "path": [
                        "vtapi",
                        "v2",
                        ":virus_name",
                        "test",
                        "{{foo}}"
                    ],
                    "variable": [
                        {
                            "key": "virus_name",
                            "value": ""
                        }
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
            collection=json.load(open(path)),
            name='VirusTotal',
            context_path_prefix=None,
            command_prefix=None
        )

        integration_code = config.generate_integration_python_code()
        integration_obj = config.generate_integration_yml()
        integration_yml = yaml.dump(integration_obj.to_dict())

        assert "foo = args.get('foo')" in integration_code
        assert "virus_name = args.get('virus_name')" in integration_code
        assert "def test_report_request(self, foo, virus_name, resource):" in integration_code
        assert "'GET', f'vtapi/v2/{virus_name}/test/{foo}', params=params, headers=headers)" in integration_code

        assert 'name: foo' in integration_yml
        assert 'name: virus_name' in integration_yml

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
            collection=json.load(open(path)),
            name=None,
            command_prefix=None,
            context_path_prefix=None,
            category=None
        )

        assert _testutil_get_param(config, 'api_key') is not None
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
            collection=json.load(open(path)),
            name=None,
            command_prefix=None,
            context_path_prefix=None,
            category=None
        )

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
        integration_yml = yaml.dump(integration_obj.to_dict())

        assert 'def test_create_group_request(self, test_name, test_id, test_key):' in integration_code
        assert 'data = {"test_filter": {"test_key": test_key}, "test_id": test_id, "test_name": test_name}' in integration_code
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


def _testutil_create_postman_collection(dest_path, with_request: Optional[dict] = None, no_auth: bool = False):
    default_collection_path = os.path.join(
        git_path(),
        'demisto_sdk',
        'commands',
        'postman_codegen',
        'tests',
        'test_files',
        'VirusTotal.postman_collection.json'
    )
    with open(default_collection_path) as f:
        collection = json.load(f)

    if with_request:
        collection['item'].append(with_request)

    if no_auth:
        del collection['auth']

    with open(dest_path, mode='w') as f:
        json.dump(collection, f)


def _testutil_get_param(config: IntegrationGeneratorConfig, param_name: str):
    if config.params is not None:
        for param in config.params:
            if param.name == param_name:
                return param

    return None


def _testutil_get_command(config: IntegrationGeneratorConfig, command_name: str):
    if config.commands is not None:
        for command in config.commands:
            if command.name == command_name:
                return command
    return None
