from copy import deepcopy
from unittest.mock import ANY

import pytest

from demisto_sdk.commands.test_content.ParallelLoggingManager import ParallelLoggingManager
from demisto_sdk.commands.test_content.TestContentClasses import Integration, BuildContext, TestResults

CONFIGURATION = {
    'configuration': [
        {
            'defaultValue': '',
            'display': 'Incident type',
            'displayPassword': '',
            'hidden': False,
            'hiddenPassword': False,
            'hiddenUsername': False,
            'info': '',
            'name': 'incidentType',
            'options': None,
            'required': False,
            'type': 13,
            'value': ''
        },

    ],
    'name': 'example_integration',
    'category': ''
}

INCIDENT_CASES = [
    (
        {"incident_type": "Example Type"},  # case only incident type
        {'incident_type': 'Example Type', 'classifier': '', 'mapper': ''}
    ),
    (
        {
            "incident_type": "Example Type",
            "classifier_id": "Example Classifier",
            "incoming_mapper_id": "Example Mapper"}  # case both incident type and classifier/mapper
        , {'incident_type': 'Example Type', 'classifier': 'Example Classifier', 'mapper': 'Example Mapper'}
    ),
    (
        {
            "classifier_id": "Example Classifier",
            "incoming_mapper_id": "Example Mapper"}  # case both incident type and classifier/mapper
        , {'incident_type': '', 'classifier': 'Example Classifier', 'mapper': 'Example Mapper'}
    ),
    ({},  # case no incident configuration provided
     {'incident_type': '', 'classifier': '', 'mapper': ''})
]


@pytest.mark.parametrize('incident_configuration, expected', INCIDENT_CASES)
def test_create_module(mocker, incident_configuration, expected):
    """
    Given:

    When:

    Then:
    """

    class Dummyconf:
        unmockable_integrations = []

    test_build_params = {'api_key': '', 'server': '', 'conf': '', 'secret': '', 'nightly': '', 'circleci': '',
                         'slack': '',
                         'build_number': '', 'branch_name': '', 'is_ami': '', 'mem_check': '', 'server_version': ''}
    mocker.patch.object(BuildContext, '_load_conf_files', return_value=(Dummyconf(), ''))
    mocker.patch.object(BuildContext, '_load_env_results_json')
    mocker.patch.object(BuildContext, '_get_server_numeric_version')
    mocker.patch.object(BuildContext, '_get_instances_ips')
    mocker.patch.object(BuildContext, '_extract_filtered_tests')
    mocker.patch.object(BuildContext, '_get_unmockable_tests_from_conf')
    mocker.patch.object(BuildContext, '_get_tests_to_run', return_value=('', ''))
    mocker.patch.object(BuildContext, '_retrieve_slack_user_id')
    mocker.patch.object(BuildContext, '_get_all_integration_config')

    test_integration = Integration(BuildContext(test_build_params, ParallelLoggingManager('temp_log')),
                                   'example_integration', [])

    res_module = test_integration.create_module(instance_name='test', configuration=deepcopy(CONFIGURATION),
                                                incident_configuration=incident_configuration)
    assert res_module.get('configuration').get('configuration')[0].get('value') == expected.get('incident_type')
    assert res_module.get('incomingMapperId') == expected.get('mapper')
    assert res_module.get('mappingId') == expected.get('classifier')

