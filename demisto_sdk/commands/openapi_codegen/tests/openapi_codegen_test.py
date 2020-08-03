import json
import os

from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.openapi_codegen.openapi_codegen import \
    OpenAPIIntegration

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

expected_request_function = '''
    def get_pet_by_id_request(self, petId):

        headers = self._headers
        

        response = self._http_request('get', f'pet/{petId}', headers=headers)

        return response

'''


class TestOpenAPICodeGen:
    test_files_path = os.path.join(git_path(), 'demisto_sdk', 'tests', 'test_files')
    swagger_path = os.path.join(test_files_path, 'swagger_pets.json')

    def init_integration(self):
        base_name = 'TestSwagger'
        integration = OpenAPIIntegration(self.swagger_path, base_name,
                                         '-'.join(base_name.split(' ')).lower(),
                                         base_name.replace(' ', ''),
                                         unique_keys='id',
                                         root_objects='Pet')

        integration.load_file()
        return integration

    def test_config_file(self, mocker):
        from demisto_sdk.commands.common.hook_validations.docker import DockerImageValidator

        mocker.patch.object(DockerImageValidator, 'get_docker_image_latest_tag_request', return_value='3.8.3.9324')

        integration = self.init_integration()
        integration.generate_configuration()

        with open(os.path.join(self.test_files_path, 'swagger_config.json'), 'rb') as config_path:
            config = json.load(config_path)

        assert json.dumps(config) == json.dumps(integration.configuration)

    def test_yaml_file(self):
        import yaml
        integration = self.init_integration()

        with open(os.path.join(self.test_files_path, 'swagger_yaml.yml'), 'rb') as yaml_file:
            expected_yaml = yaml.safe_load(yaml_file)

        yaml_obj = integration.generate_yaml().to_yaml()

        assert yaml.dump(expected_yaml) == yaml.dump(yaml_obj)



    def test_get_command_function(self):
        integration = self.init_integration()
        command = [c for c in integration.configuration['commands'] if c['name'] == 'get-pet-by-id'][0]

        command_function, req_function = integration.get_python_command_and_request_functions(command)

        assert expected_command_function == command_function
        assert expected_request_function == req_function

    def test_command_body_args(self):
        from demisto_sdk.commands.openapi_codegen.openapi_codegen import base_data
        integration = self.init_integration()
        command = [c for c in integration.configuration['commands'] if c['name'] == 'create-user'][0]

        expected_args = 'id=user_id, username=user_username, firstName=user_firstname, lastName=user_lastname,' \
                        ' email=user_email, password=user_password, phone=user_phone, userStatus=user_userstatus'

        arguments = integration.process_command_arguments(command)
        body_args = integration.format_params(arguments[3], base_data, base_data)
        assert expected_args == body_args

    def test_command_headers(self):
        integration = self.init_integration()
        command = [c for c in integration.configuration['commands'] if c['name'] == 'upload-file'][0]

        expected_headers = [{'Content-Type': 'multipart/form-data'}]

        assert expected_headers == command['headers']


