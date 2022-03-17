import os

from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.openapi_codegen.openapi_codegen import \
    OpenAPIIntegration

json = JSON_Handler()


yaml = YAML_Handler()
expected_command_function = '''def get_pet_by_id_command(client: Client, args: Dict[str, Any]) -> CommandResults:
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

expected_request_function = ('    def get_pet_by_id_request(self, petId):\n'
                             '        headers = self._headers\n'
                             '\n'
                             '        response = self._http_request(\'get\', f\'pet/{petId}\', headers=headers)\n'
                             '\n'
                             '        return response\n')


class TestOpenAPICodeGen:
    test_files_path = os.path.join(git_path(), 'demisto_sdk', 'tests', 'test_files')
    swagger_path = os.path.join(test_files_path, 'swagger_pets.json')

    def init_integration(self, base_name: str = 'TestSwagger'):
        integration = OpenAPIIntegration(self.swagger_path, base_name,
                                         '-'.join(base_name.split(' ')).lower(),
                                         base_name.replace(' ', ''),
                                         unique_keys='id',
                                         root_objects='Pet',
                                         fix_code=True)

        integration.load_file()
        return integration

    def test_config_file(self, mocker):
        """
        Scenario: Generating an integration from a swagger file

        Given
            - A swagger file
        When
            - Generating the integration configuration file for the swagger file
        Then
            - Ensure the configuration file is generated correctly
        """
        from demisto_sdk.commands.common.hook_validations.docker import \
            DockerImageValidator

        mocker.patch.object(DockerImageValidator, 'get_docker_image_latest_tag_request', return_value='3.8.6.12176')

        integration = self.init_integration()
        integration.generate_configuration()

        with open(os.path.join(self.test_files_path, 'swagger_config.json'), 'rb') as config_path:
            config = json.load(config_path)

        assert json.dumps(integration.configuration) == json.dumps(config)

    def test_yaml_file(self, mocker):
        """
        Scenario: Generating an integration from a swagger file

        Given
           - A swagger file
           - A generated integration configuration file
        When
           - Generating the integration yaml
        Then
           - Ensure the yaml file is generated correctly
       """

        from demisto_sdk.commands.common.hook_validations.docker import \
            DockerImageValidator

        mocker.patch.object(DockerImageValidator, 'get_docker_image_latest_tag_request', return_value='3.8.6.12176')
        integration = self.init_integration()

        with open(os.path.join(self.test_files_path, 'swagger_yaml.yml'), 'rb') as yaml_file:
            expected_yaml = yaml.load(yaml_file)

        yaml_obj = integration.generate_yaml().to_dict()

        assert yaml_obj == expected_yaml

    def test_python_file(self):
        """
        Scenario: Generating an integration from a swagger file

        Given
           - A swagger file
           - A generated integration configuration file
        When
           - Generating the integration python code
        Then
           - Ensure the python file is generated correctly
       """
        integration = self.init_integration()

        with open(os.path.join(self.test_files_path, 'swagger_python.py'), 'r') as py_file:
            expected_py = py_file.read()

        py = integration.generate_python_code()
        assert py == expected_py

    def test_get_command_function(self):
        """
        Scenario: Generating an integration from a swagger file

        Given
           - A swagger file
           - A generated integration configuration file
           - Generated commands from the configuration file
        When
           - Generating a command function and a request function for a command
        Then
           - Ensure the commands are generated correctly
        """
        integration = self.init_integration()
        command = [c for c in integration.configuration['commands'] if c['name'] == 'get-pet-by-id'][0]

        command_function, req_function = integration.get_python_command_and_request_functions(command)

        assert command_function == expected_command_function
        assert req_function == expected_request_function

    def test_command_body_args(self):
        """
        Scenario: Generating an integration from a swagger file

        Given
           - A swagger file
           - A generated integration configuration file
           - Generated commands from the configuration file
        When
           - Generating arguments for the command request body
        Then
           - Ensure the arguments are generated correctly
        """
        from demisto_sdk.commands.openapi_codegen.openapi_codegen import \
            BASE_DATA
        integration = self.init_integration()
        command = [c for c in integration.configuration['commands'] if c['name'] == 'create-user'][0]

        expected_args = 'id=user_id, username=user_username, firstName=user_firstname, lastName=user_lastname,' \
                        ' email=user_email, password=user_password, phone=user_phone, userStatus=user_userstatus'

        arguments = integration.process_command_arguments(command)
        body_args = integration.format_params(arguments[3], BASE_DATA, BASE_DATA)
        assert expected_args == body_args

    def test_command_headers(self):
        """
        Scenario: Generating an integration from a swagger file

        Given
           - A swagger file
           - A generated integration configuration file
           - Generated commands from the configuration file
        When
           - Generating headers for the command request
        Then
           - Ensure the headers are generated correctly
        """
        integration = self.init_integration()
        command = [c for c in integration.configuration['commands'] if c['name'] == 'post-pet-upload-image'][0]

        expected_headers = [{'Content-Type': 'multipart/form-data'}]

        assert expected_headers == command['headers']

    def test_change_name_duplications(self):
        """
        Scenario: Generating an integration from a swagger file

        Given
           - A swagger file
           - A generated integration configuration file
           - Generated commands from the configuration file (added command with same summary but different path)
        When
           - Generating functions name.
        Then
           - Ensure that the names of given functions generated correctly.
        """

        integration = self.init_integration()
        assert [c for c in integration.configuration['commands'] if c['name'] == 'post-pet-upload-image'][0]
        assert [c for c in integration.configuration['commands'] if c['name'] ==
                'post-pet-upload-image-by-uploadimage'][0]

    def test_file_not_overwritten(self):
        """
        Given:
        - Configurations

        When:
        - Saving configuration file

        Then:
        - Ensure file does not overwrite given JSON file for open API code gen command.
        """
        integration = self.init_integration(base_name='swagger_pets')
        with open(self.swagger_path, 'r') as f:
            file_data_before_config_save = json.loads(f.read())
        integration.save_config(integration.configuration, self.test_files_path)
        with open(self.swagger_path, 'r') as f:
            file_data_after_config_save = json.loads(f.read())
        assert file_data_after_config_save == file_data_before_config_save
        os.remove(os.path.join(self.test_files_path, f'{integration.base_name}_config.json'))

    def test_ref_props_non_dict_handling(self):
        """
        Test added according to reported issue of 'str' object has no attribute 'items'.
        This test runs extract outputs commands with properties that are not dict, and expects to pass.

        Given:
        - Dict containing data.

        When:
        - Extracting outputs from the given data.

        Then:
        - Ensure extract outputs does not stop on 'str' object has no attribute 'items' error.
        """
        base_name = 'TestSwagger'
        integration = OpenAPIIntegration(self.swagger_path, base_name,
                                         '-'.join(base_name.split(' ')).lower(),
                                         base_name.replace(' ', ''),
                                         unique_keys='id',
                                         root_objects='Pet',
                                         fix_code=True)
        integration.reference = {'example': {'properties': 'type: object'}, 'example2': {'properties': {'data': 2}}}
        data = {
            'responses': {
                '200': {
                    'description': 'Response number one',
                    'schema': [
                        {
                            '$ref': '#/ref/example'
                        }
                    ]
                }
            }
        }
        integration.extract_outputs(data)
