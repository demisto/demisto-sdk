from unittest.mock import ANY

from demisto_sdk.commands.test_content.TestContentClasses import (
    Integration, IntegrationConfiguration, TestConfiguration, TestPlaybook)
from demisto_sdk.commands.test_content.tests.build_context_test import \
    get_mocked_build_context
from demisto_sdk.commands.test_content.tests.DemistoClientMock import \
    DemistoClientMock
from demisto_sdk.commands.test_content.tests.server_context_test import \
    generate_mocked_server_context


def test_set_prev_server_keys(mocker, tmp_path):
    """
    Given:
        - Test playbook and integration to run
        - Integration config with server keys (python.pass.extra.keys)

    When:
        - Cleaning server config when disabling the integration instance

    Then:
        - Ensure _clear_server_keys() return True to verify it updated the server config
        - Verify update_server_conf_func called with prev server conf
    """
    prev_server_conf = {'prev': 'conf'}
    mocked_demisto_client = DemistoClientMock()
    build_context = get_mocked_build_context(mocker, tmp_path)
    server_context = generate_mocked_server_context(build_context, mocked_demisto_client, mocker)
    update_server_conf_func = mocker.patch(
        'demisto_sdk.commands.test_content.TestContentClasses.update_server_configuration',
        return_value=(None, None, prev_server_conf)
    )
    test_playbook_configuration = TestConfiguration({}, 0)

    test_playbook = TestPlaybook(build_context, test_playbook_configuration)
    integration = Integration(build_context, 'integration_with_server_keys', ['instance'])
    integration.configuration = IntegrationConfiguration({
        'params': {
            'server_keys': {
                'python.pass.extra.keys': '--hostname=HOSTNAME##-v=test1234'
            }
        }
    })

    integration._set_server_keys(mocked_demisto_client, server_context)
    test_playbook.integrations = [integration]

    assert test_playbook._set_prev_server_keys(mocked_demisto_client, server_context)

    update_server_conf_func.assert_called_with(
        client=mocked_demisto_client,
        server_configuration=prev_server_conf,
        error_msg='Failed to set server keys',
        logging_manager=ANY
    )
