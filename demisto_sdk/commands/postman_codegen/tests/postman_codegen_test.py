import json
import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Union

import pytest
import yaml
from click.testing import CliRunner

import demisto_sdk.commands.common.tools as tools
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.generate_integration.code_generator import (
    IntegrationGeneratorArg, IntegrationGeneratorConfig,
    IntegrationGeneratorOutput)
from demisto_sdk.commands.postman_codegen.postman_codegen import (
    build_commands_names_dict, create_body_format, duplicate_requests_check,
    find_shared_args_path, flatten_collections, generate_command_outputs,
    postman_to_autogen_configuration, update_min_unique_path)


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

    def test_create_body_format_different_arg_name_nested(self):
        """
        Given
        - Request body and a list of arguments.

        When
        - There are two arguments, both nested in other arguments, with the same name and different paths.

        Then
        - Creates a body format with the right arguments' names.
        """
        request_body = {
            "key5": {
                "key3": "val3"
            },
            "key2": {
                "key6": {
                    "key3": "val3",
                    "key8": "val8"
                }
            }
        }

        args: List[IntegrationGeneratorArg] = [
            IntegrationGeneratorArg(name="key5", description='', in_='body', in_object=[]),
            IntegrationGeneratorArg(name="key5_key3", description='', in_='body', in_object=["key5"]),
            IntegrationGeneratorArg(name="key2", description='', in_='body', in_object=[]),
            IntegrationGeneratorArg(name="key6", description='', in_='body', in_object=["key2"]),
            IntegrationGeneratorArg(name="key6_key3", description='', in_='body', in_object=["key2", "key6"]),
            IntegrationGeneratorArg(name="key8", description='', in_='body', in_object=["key2", "key6"]),
        ]
        body_format = create_body_format(request_body, args)

        assert body_format == {
            "key5": {
                "key3": "{key5_key3}"
            },
            "key2": {
                "key6": {
                    "key3": "{key6_key3}",
                    "key8": "{key8}"
                }
            }
        }

    def test_create_body_format_different_arg_name_one_nested(self):
        """
        Given
        - Request body and a list of arguments.

        When
        - There are two arguments, one of them nested in another argument, with the same name and different paths.

        Then
        - Creates a body format with the right arguments' names.
        """
        request_body = {
            "key1": "val1",
            "key4": [
                {
                    "key1": "val5"
                }
            ]
        }

        args: List[IntegrationGeneratorArg] = [
            IntegrationGeneratorArg(name="key1", description='', in_='body', in_object=[]),
            IntegrationGeneratorArg(name="key4", description='', in_='body', in_object=[]),
            IntegrationGeneratorArg(name="key4_key1", description='', in_='body', in_object=["key4"]),
        ]
        body_format = create_body_format(request_body, args)

        assert body_format == {
            "key1": "{key1}",
            "key4": [
                {
                    "key1": "{key4_key1}"
                },
            ],
        }

    @pytest.mark.parametrize('collection, outputs', [
        ([], []),
        ([[], []], []),
        ([{}, [], [{}]], [{}, {}]),
        ([{'item': [{}]}, [], [{}]], [{}, {}])
    ])
    def test_flatten_collections(self, collection: list, outputs: list):
        assert flatten_collections(collection) == outputs

    def test_build_commands_names_dict_duplicate_names(self):
        """
        Given
        - dictionary containing names of requests from a collection

        When
        - There are requests with names which have the same kebab case

        Then
        - returns names' dictionary with an entry of the matching kebab-case which has a list with the problematic names
        """
        requests = [
            {
                "name": "Test Number One"
            },
            {
                "name": "Test number  one"
            },
            {
                "name": "Test number two"
            }
        ]
        names_dict = build_commands_names_dict(requests)
        assert len(names_dict[tools.to_kebab_case("Test Number One")]) == 2
        assert len(names_dict[tools.to_kebab_case("Test number two")]) == 1
        assert len(names_dict) == 2

    def test_build_commands_names_dict_no_duplicate_names(self):
        """
        Given
        - dictionary containing names of requests from a collection

        When
        - There are no requests with names which have the same kebab case

        Then
        - returns names' dictionary with an entry for each request's name kebab case and the original name
        """
        requests = [
            {
                "name": "Test Number One"
            },
            {
                "name": "Test number two"
            }
        ]
        names_dict = build_commands_names_dict(requests)
        assert len(names_dict[tools.to_kebab_case("Test Number One")]) == 1
        assert len(names_dict[tools.to_kebab_case("Test number two")]) == 1
        assert len(names_dict) == 2

    def test_build_commands_names_dict_none_names(self):
        """
        Given
        - dictionary containing names of requests from a collection

        When
        - There's a request with no name key

        Then
        - returns names' dictionary with an entry for each request's name kebab case and the original name and just them
        """
        requests = [
            {
                "None": None
            },
            {
                "name": "Test number  one"
            },
            {
                "name": "Test number two"
            }
        ]
        names_dict = build_commands_names_dict(requests)
        assert len(names_dict[tools.to_kebab_case("Test Number One")]) == 1
        assert len(names_dict[tools.to_kebab_case("Test number two")]) == 1
        assert len(names_dict) == 2

    def test_duplicate_requests_check_duplicates_exist(self):
        """
        Given
        - dictionary containing names in kebab case of requests and a list with their original names

        When
        - There are requests with the same kebab case

        Then
        - throw assertion error with the problematic requests' names
        """
        with pytest.raises(Exception):
            names_dict = {
                'test-number-one': [
                    "Test number  one",
                    "Test Number One"
                ],
                'test-number-two': [
                    "Test number two"
                ]
            }
            duplicate_requests_check(names_dict)

    def test_duplicate_requests_check_duplicates_dont_exist(self):
        """
        Given
        - dictionary containing names in kebab case of requests and a list with their original names

        When
        - There are no requests with the same kebab case

        Then
        - don't throw assertion error
        """
        names_dict = {
            'test-number-one': [
                "Test number  one",
            ],
            'test-number-two': [
                "Test number two"
            ]
        }
        duplicate_requests_check(names_dict)

    test_files_path = os.path.join(git_path(), 'demisto_sdk', 'commands', 'postman_codegen', 'tests', 'test_files')
    with open(os.path.join(test_files_path, 'shared_args_path.json')) as shared_args_path_file:
        shared_args_path_items = json.load(shared_args_path_file)

    many_with_shared_paths = defaultdict(int, {'name': 2, 'description': 3, 'url': 3, 'method': 3})
    one_shared_for_each_paths = defaultdict(int, {'name': 1, 'id': 1, 'uid': 1})
    complicated_chars_in_paths = defaultdict(int, {'name': 1, 'required': 5})
    same_path_at_the_end = defaultdict(int, {'name': 2})
    SHARED_ARGS_PATH = ((shared_args_path_items['many_with_shared_paths'], many_with_shared_paths),
                        (shared_args_path_items['one_shared_for_each_paths'], one_shared_for_each_paths),
                        (shared_args_path_items['complicated_chars_in_paths'], complicated_chars_in_paths),
                        (shared_args_path_items['same_path_at_the_end'], same_path_at_the_end))

    @pytest.mark.parametrize('flattened_json, shared_arg_to_split_position_dict', SHARED_ARGS_PATH)
    def test_find_shared_args_path(self, flattened_json, shared_arg_to_split_position_dict):
        """
        Given
        - Dictionary containing flattened json with raw body of a request

        When
        - There are arguments in the request which have the same name (suffix)

        Then
        - Returns arguments' dictionary with an entry for each argument name, that holds the minimum distinguishing shared path of
        all arguments with the same name
        """
        for arg_name, min_path_length in find_shared_args_path(flattened_json).items():
            assert shared_arg_to_split_position_dict[arg_name] == min_path_length

    def test_find_shared_args_path_no_path(self):
        """
        Given
        - Dictionary containing flattened json with raw body of a request, that doesn't have duplicate names

        When
        - There are no arguments in the request which have the same name (suffix)

        Then
        - Returns arguments' dictionary with an entry for each argument name, that holds the minimum distinguishing shared path of
        all arguments with the same name - which is 0 in this case
        """
        flattened_json = {
            "strategy": "deleteSource",
            "source": "{{source_collection_uid}}",
            "destination": "{{destination_collection_uid}}"
        }
        shared_arg_to_split_position_dict = defaultdict(int)
        for arg_name, min_path_length in find_shared_args_path(flattened_json).items():
            assert shared_arg_to_split_position_dict[arg_name] == min_path_length

    split_path1 = ['collection', 'item', 'settings', 'name']
    split_path2 = ['collection', 'info', 'settings', 'name']
    split_path3 = ['collection', 'item', 'property', 'name']
    split_path4 = ['set', 'item', 'property', 'name']

    first_call = (split_path2, [], 0, 0)
    max_to_bigger_then_zero = (split_path4, [split_path2], 0, 1)
    max_changes_on_first_item = (split_path4, [split_path3, split_path2, split_path1], 2, 3)
    max_changes_on_second_item = (split_path1, [split_path3, split_path2], 1, 2)
    max_doesnt_change = (split_path3, [split_path1, split_path2], 2, 2)
    UPDATED_MAX_INPUT = (first_call,
                         max_to_bigger_then_zero,
                         max_changes_on_first_item,
                         max_changes_on_second_item,
                         max_doesnt_change)

    @pytest.mark.parametrize('split_path, other_args_split_paths, current_min_unique, new_min_unique', UPDATED_MAX_INPUT)
    def test_update_min_distinguish_path(self, split_path, other_args_split_paths, current_min_unique, new_min_unique):
        """
        Given
        - A split path of an argument, a list of other arguments' splitted paths, and the minimum unique path until now

        When
        - Finding the minimum unique path between the arguments that have the same name

        Then
        - Returns the minimum unique path of all arguments with the same name
        """
        assert update_min_unique_path(split_path, other_args_split_paths, current_min_unique) == new_min_unique


class TestPostmanCodeGen:
    test_files_path = os.path.join(git_path(), 'demisto_sdk', 'commands', 'postman_codegen', 'tests', 'test_files')
    postman_collection_stream = None
    autogen_config_stream = None
    postman_collection: dict
    autogen_config: dict
    arguments_check_collection: dict

    @classmethod
    def setup_class(cls):
        collection_path = os.path.join(cls.test_files_path, 'VirusTotal.postman_collection.json')
        autogen_config_path = os.path.join(cls.test_files_path, 'VirusTotal-autogen-config.json')
        arguments_check_collection_path = os.path.join(cls.test_files_path, 'arguments_check_collection.json')
        with open(collection_path) as f:
            cls.postman_collection = json.load(f)

        with open(autogen_config_path) as f:
            cls.autogen_config = json.load(f)

        with open(arguments_check_collection_path) as f:
            cls.arguments_check_collection = json.load(f)

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

    def test_command_arguments_names_duplication(self):
        """
        Given
        - postman collection with one command, that has some arguments with the same name (suffix)

        When
        - generating config file

        Then
        - ensure the number of arguments generated is the same as the number of arguments in the command (if not, some arguments
        are generated as one with the same name)
        """
        autogen_config = postman_to_autogen_configuration(
            collection=self.arguments_check_collection,
            command_prefix=None,

            name=None,
            context_path_prefix=None,
            category=None
        )
        assert len(autogen_config.commands[0].arguments) == 15

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
        {{url}}/vtapi/v2/:Virus_name/test/{{foo}}?resource=https://www.cobaltstrike.com/

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
                    "raw": "{{url}}/vtapi/v2/:Virus_name/test/{{foo}}?resource=https://www.cobaltstrike.com/",
                    "host": [
                        "{{url}}"
                    ],
                    "path": [
                        "vtapi",
                        "v2",
                        ":Virus_name",
                        "test",
                        "{{foo}}"
                    ],
                    "variable": [
                        {
                            "key": "Virus_name",
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

    def test_args_lowercase(self, tmp_path):
        """
        Given
        - Postman collection.
        - Test report request which has variables with upper case.

        When
        - Generating config file.

        Then
        - Integration code has arguments as lowercase, but sends the arguments to requests as given.
        - Integration yml, the arguments are lower case.
        """
        path = tmp_path / 'test-collection.json'
        _testutil_create_postman_collection(dest_path=path, with_request={
            "name": "Test Report",
            "request": {
                "method": "GET",
                "header": [],
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"A\": 2,\n    \"B\": 3,\n    \"c\": 4\n}"
                },
                "url": {
                    "raw": "{{url}}/vtapi/v2/test/{{FOO_A}}?RESOURCE_B=https://www.cobaltstrike.com/",
                    "host": [
                        "{{url}}"
                    ],
                    "path": [
                        "vtapi",
                        "v2",
                        "test",
                        "{{FOO_A}}"
                    ],
                    "query": [
                        {
                            "key": "RESOURCE_B",
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

        assert "foo_a = args.get('foo_a')" in integration_code
        assert "def test_report_request(self, foo_a, resource_b, a, b, c)" in integration_code
        assert 'assign_params(RESOURCE_B=resource_b' in integration_code
        assert "('GET', f'vtapi/v2/test/{foo_a}', params=params, json_data=data, headers=headers)" in integration_code

        assert 'name: foo_a' in integration_yml
        assert 'name: resource_b' in integration_yml
        assert 'name: a\n' in integration_yml
        assert 'name: b\n' in integration_yml
        assert 'name: c\n' in integration_yml

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

    GENERATE_COMMAND_OUTPUTS_INPUTS = [({'id': 1}, [IntegrationGeneratorOutput('id', '', 'Number')]),
                                       ([{'id': 1}], [IntegrationGeneratorOutput('id', '', 'Number')]),
                                       ([{'a': [{'b': 2}]}], [IntegrationGeneratorOutput('a.b', '', 'Number')])]

    @pytest.mark.parametrize('body, expected', GENERATE_COMMAND_OUTPUTS_INPUTS)
    def test_generate_command_outputs(self, body: Union[List, Dict], expected: List[IntegrationGeneratorOutput]):
        """
        Given:
        - Body of postman generator command.

        When:
        - Building corresponding command for Cortex XSOAR.

        Then:
        - Ensure outputs are flattened correctly.
        """
        outputs: List[IntegrationGeneratorOutput] = generate_command_outputs(body)
        for i in range(len(outputs)):
            assert outputs[i].name == expected[i].name
            assert outputs[i].description == expected[i].description
            assert outputs[i].type_ == expected[i].type_
        assert len(outputs) == len(expected)

    def test_package_integration_generation(self, tmp_path):
        """
        Given
        - postman collection
        When
        - generating an integration in a package format
        Then
        - package should be created with the integration files.
        """
        package_path = os.path.join(self.test_files_path, 'package')
        os.mkdir(package_path)
        collection_path = os.path.join(self.test_files_path, 'VirusTotal.postman_collection.json')
        try:
            runner = CliRunner()
            runner.invoke(main, ['postman-codegen', '-i', collection_path,
                                 '-o', package_path, '-p'], catch_exceptions=False)
            assert all(elem in os.listdir(package_path) for elem in ['package.py', 'README.md', 'package.yml'])
        except Exception as e:
            raise e
        finally:
            shutil.rmtree(package_path)


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
