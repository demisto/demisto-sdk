from unittest.mock import ANY

from demisto_sdk.commands.test_content.TestContentClasses import (
    Integration, IntegrationConfiguration, TestConfiguration, TestPlaybook)
from demisto_sdk.commands.test_content.tests.DemistoClientMock import \
    DemistoClientMock


def test_c(mocker):
    """
    Given:
        - Test playbook and integration to run
        - Integration config with server keys (python.pass.extra.keys)

    When:
        - Cleaning server config when disabling the integration instance

    Then:
        - Ensure _clear_server_keys() return True to verify it updated the server config
        - Verify update_server_conf_func called with empty python.pass.extra.keys
    """
    test_playbook_configuration = TestConfiguration({}, 0)
    test_playbook = TestPlaybook(mocker.MagicMock(), test_playbook_configuration)
    integration = Integration(mocker.MagicMock(), 'integration_with_server_keys', ['instance'])
    integration.configuration = IntegrationConfiguration({
        'params': {
            'server_keys': {
                'python.pass.extra.keys': '--hostname=HOSTNAME##-v=test1234'
            }
        }
    })
    test_playbook.integrations = [integration]
    mocked_demisto_client = DemistoClientMock()
    update_server_conf_func = mocker.patch(
        'demisto_sdk.commands.test_content.TestContentClasses.update_server_configuration'
    )

    assert test_playbook._clear_server_keys(mocked_demisto_client)

    update_server_conf_func.assert_called_with(
        client=mocked_demisto_client,
        server_configuration={'python.pass.extra.keys': ''},
        error_msg='Failed to set server keys',
        logging_manager=ANY
    )
