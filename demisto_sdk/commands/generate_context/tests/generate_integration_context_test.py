import os

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_json, get_yaml

FILES_PATH = os.path.normpath(
    os.path.join(__file__, git_path(), 'demisto_sdk', 'tests', 'test_files'))
FAKE_INTEGRATION_YML = get_yaml(
    os.path.join(FILES_PATH, 'fake_integration.yml'))
FAKE_OUTPUT_CONTEXTS = get_json(
    os.path.join(FILES_PATH, 'fake_outputs_with_contexts.json'))
FAKE_EXAMPLES_FILE = os.path.join(FILES_PATH, 'fake_examples.txt')


def test_generate_context_from_outputs():
    """
    Given
        - A string representing an example output json
    When
        - generating context objects
    Then
        - Ensure the outputs are correct
    """
    from demisto_sdk.commands.generate_context.generate_integration_context import \
        dict_from_outputs_str

    EXAMPLE_INT_OUTPUTS = '''{'Guardicore': {'Endpoint': {'asset_id': '1-2-3-4-5',
'ip_addresses': ['1.1.1.1',
              'ffe::fef:fefe:fefee:fefe'],
'last_seen': 1629200550561,
'name': 'Accounting-web-1',
'status': 'on',
'tenant_name': 'esx10/lab_a/Apps/Accounting'}}}'''

    assert dict_from_outputs_str('!some-test-command=172.16.1.111',
                                 EXAMPLE_INT_OUTPUTS) == \
        {
        'arguments': [],
        'name': 'some-test-command=172.16.1.111',
        'outputs': [{'contextPath': 'Guardicore.Endpoint.asset_id',
                     'description': '',
                     'type': 'String'},
                    {'contextPath': 'Guardicore.Endpoint.ip_addresses',
                     'description': '',
                     'type': 'String'},
                    {'contextPath': 'Guardicore.Endpoint.last_seen',
                     'description': '',
                     'type': 'Date'},
                    {'contextPath': 'Guardicore.Endpoint.name',
                     'description': '',
                     'type': 'String'},
                    {'contextPath': 'Guardicore.Endpoint.status',
                     'description': '',
                     'type': 'String'},
                    {'contextPath': 'Guardicore.Endpoint.tenant_name',
                     'description': '',
                     'type': 'String'}]}


def test_generate_example_dict(mocker):
    """
    Given
       - An exmaples file path
    When
       - generating examples outputs
    Then
       - Ensure the outputs are correct
    """
    import demisto_sdk.commands.generate_docs.common

    os.environ["DEMISTO_BASE_URL"] = "1"
    os.environ["DEMISTO_USERNAME"] = "1"
    os.environ["DEMISTO_PASSWORD"] = "1"
    mocker.patch.object(demisto_sdk.commands.generate_docs.common,
                        'build_example_dict',
                        return_value=(FAKE_OUTPUT_CONTEXTS, []))
    from demisto_sdk.commands.generate_context.generate_integration_context import \
        generate_example_dict

    assert generate_example_dict(FAKE_EXAMPLES_FILE) == FAKE_OUTPUT_CONTEXTS


def test_insert_outputs(mocker):
    """
    Given
      - A yaml file and fake example outputs
    When
      - inserting those examples into the yml
    Then
      - Ensure the outputs are inserted correctly
    """
    import demisto_sdk.commands.generate_docs.common
    os.environ["DEMISTO_BASE_URL"] = "1"
    os.environ["DEMISTO_USERNAME"] = "1"
    os.environ["DEMISTO_PASSWORD"] = "1"
    mocker.patch.object(demisto_sdk.commands.generate_docs.common,
                        'build_example_dict',
                        return_value=(FAKE_OUTPUT_CONTEXTS, []))
    from demisto_sdk.commands.generate_context.generate_integration_context import \
        insert_outputs

    yml_data = FAKE_INTEGRATION_YML

    command = 'zoom-fetch-recording'
    yml_data = insert_outputs(yml_data, command, FAKE_OUTPUT_CONTEXTS)
    for command in yml_data['script']['commands']:
        if command.get('name') == command:
            assert command['outputs'] == FAKE_OUTPUT_CONTEXTS
            break
