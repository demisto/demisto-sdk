import os

from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.openapi_codegen.openapi_codegen import \
    OpenAPIIntegration


class TestOpenAPICodeGen:
    swagger_path = os.path.join(git_path(), 'demisto_sdk', 'tests', 'test_files', 'swagger_pets.json')

    def init_integration(self):
        base_name = 'TestSwagger'
        integration = OpenAPIIntegration(self.swagger_path, base_name,
                                         '-'.join(base_name.split(' ')).lower(),
                                         base_name.replace(' ', ''),
                                         unique_keys='id',
                                         root_objects='Pet')
        return integration

    def test_get_command_function(self):
        integration = self.init_integration()
        integration.load_file()
        command = integration.configuration['commands'][0]

        function, req_function = integration.get_python_command_and_request_functions(command)

        print(str(function))
