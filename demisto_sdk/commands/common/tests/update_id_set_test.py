import json
import os
import shutil
import sys
import tempfile
import unittest
from tempfile import mkdtemp

import pytest
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.update_id_set import (find_duplicates,
                                                       get_integration_data,
                                                       get_playbook_data,
                                                       get_script_data,
                                                       has_duplicate,
                                                       re_create_id_set)
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator

TESTS_DIR = f'{git_path()}/demisto_sdk/tests'


class TestIDSetCreator:
    def setup(self):
        self.id_set_full_path = os.path.join(TESTS_DIR, 'test_files', 'content_repo_example', 'id_set.json')
        self._test_dir = mkdtemp()
        self.file_path = os.path.join(self._test_dir, 'id_set.json')

    def teardown(self):
        # delete the id set file
        try:
            if os.path.isfile(self.file_path) or os.path.islink(self.file_path):
                os.unlink(self.file_path)
            elif os.path.isdir(self.file_path):
                shutil.rmtree(self.file_path)
        except Exception as err:
            print(f'Failed to delete {self.file_path}. Reason: {err}')

    def test_create_id_set_output(self):
        id_set_creator = IDSetCreator(self.file_path)

        id_set_creator.create_id_set()
        assert os.path.exists(self.file_path)

    def test_create_id_set_no_output(self):
        id_set_creator = IDSetCreator()

        id_set = id_set_creator.create_id_set()
        assert not os.path.exists(self.file_path)
        assert id_set is not None
        assert 'scripts' in id_set.keys()
        assert 'integrations' in id_set.keys()
        assert 'playbooks' in id_set.keys()
        assert 'TestPlaybooks' in id_set.keys()
        assert 'Classifiers' in id_set.keys()
        assert 'Dashboards' in id_set.keys()
        assert 'IncidentFields' in id_set.keys()
        assert 'IncidentTypes' in id_set.keys()
        assert 'IndicatorFields' in id_set.keys()
        assert 'IndicatorTypes' in id_set.keys()
        assert 'Layouts' in id_set.keys()
        assert 'Reports' in id_set.keys()
        assert 'Widgets' in id_set.keys()
        assert 'Mappers' in id_set.keys()


class TestDuplicates:
    MOCKED_DATA = [
        (
            [
                {
                    "BluecatAddressManager": {
                        "name": "BluecatAddressManager",
                        "file_path": "Integrations/BluecatAddressManager/BluecatAddressManager.yml",
                        "fromversion": "5.0.0"
                    }
                },
                {
                    "BluecatAddressManager": {
                        "name": "BluecatAddressManager",
                        "file_path": "Integrations/BluecatAddressManager/BluecatAddressManager.yml",
                        "fromversion": "5.0.0"
                    }
                }
            ], 'BluecatAddressManager', True
        ),
        (
            [
                {
                    "BluecatAddressManager": {
                        "name": "BluecatAddressManager",
                        "file_path": "Integrations/BluecatAddressManager/BluecatAddressManager.yml",
                        "fromversion": "5.0.0"
                    }
                },
                {
                    "BluecatAddressManager": {
                        "name": "BluecatAddressManager",
                        "file_path": "Integrations/BluecatAddressManager/BluecatAddressManager.yml",
                        "fromversion": "3.1.0",
                        "toversion": "4.0.0"
                    }
                }
            ], 'BluecatAddressManager', False
        ),
        (
            [
                {
                    'Test3': {
                        'name': 'Test3',
                        'file_path': 'A',
                        'fromversion': '3.0.0',
                        'toversion': '3.6.0',
                    }
                },
                {
                    'Test3': {
                        'name': 'Test3',
                        'file_path': 'B',
                        'fromversion': '3.5.0',
                        'toversion': '4.5.0',
                    }
                },
                {
                    'Test3': {
                        'name': 'Test3',
                        'file_path': 'C',
                        'fromversion': '3.5.2',
                        'toversion': '3.5.4',
                    }
                },
                {
                    'Test3': {
                        'name': 'Test3',
                        'file_path': 'D',
                        'fromversion': '4.5.0',
                    },
                },
            ], 'Test3', True
        ),
    ]

    @staticmethod
    @pytest.mark.parametrize('id_set, id_to_check, result', MOCKED_DATA)
    def test_had_duplicates(id_set, id_to_check, result):
        assert result == has_duplicate(id_set, id_to_check)

    ID_SET = [
        {'Access': {'typeID': 'Access', 'kind': 'edit', 'path': 'Layouts/layout-edit-Access.json'}},
        {'Access': {'typeID': 'Access', 'fromversion': '4.1.0', 'kind': 'details', 'path': 'layout-Access.json'}},
        {'urlRep': {'typeID': 'urlRep', 'kind': 'Details', 'path': 'Layouts/layout-Details-url.json'}},
        {'urlRep': {'typeID': 'urlRep', 'fromversion': '5.0.0', 'kind': 'Details',
                    'path': 'layout-Details-url_5.4.9.json'}}
    ]

    INPUT_TEST_HAS_DUPLICATE = [
        ('Access', False),
        ('urlRep', True)
    ]

    @staticmethod
    @pytest.mark.parametrize('list_input, list_output', INPUT_TEST_HAS_DUPLICATE)
    def test_has_duplicate(list_input, list_output):
        """
        Given
            - A list of dictionaries with layout data called ID_SET & layout_id

        When
            - checking for duplicate

        Then
            - Ensure return true for duplicate layout
            - Ensure return false for layout with different kind
        """
        result = has_duplicate(TestDuplicates.ID_SET, list_input, 'Layouts', False)
        assert list_output == result


class TestIntegrations:
    INTEGRATION_DATA = {
        "Dummy Integration": {
            "name": "Dummy Integration",
            "file_path": TESTS_DIR + "/test_files/DummyPack/Integrations/DummyIntegration/DummyIntegration.yml",
            "fromversion": "4.1.0",
            "commands": ['xdr-get-incidents',
                         'xdr-get-incident-extra-data',
                         'xdr-update-incident',
                         'xdr-insert-parsed-alert',
                         'xdr-insert-cef-alerts',
                         'xdr-isolate-endpoint',
                         'xdr-unisolate-endpoint',
                         'xdr-get-endpoints',
                         'xdr-get-distribution-versions',
                         'xdr-create-distribution',
                         'xdr-get-distribution-url',
                         'xdr-get-create-distribution-status',
                         'xdr-get-audit-management-logs',
                         'xdr-get-audit-agent-reports'],
            "api_modules": "HTTPFeedApiModule",
            "classifiers": "dummy-classifier",
            "incident_types": "dummy-incident-type",
            "indicator_fields": "CommonTypes",
            "indicator_types": "CommonTypes",
            "mappers": [
                "dummy-mapper-in",
                "dummy-mapper-out"
            ]
        }
    }

    UNIFIED_INTEGRATION_DATA = {
        "Dummy Integration": {
            "name": "Dummy Integration",
            "file_path": TESTS_DIR + "/test_files/DummyPack/Integrations/integration-DummyIntegration.yml",
            "fromversion": "4.1.0",
            "commands": ['xdr-get-incidents',
                         'xdr-get-incident-extra-data',
                         'xdr-update-incident',
                         'xdr-insert-parsed-alert',
                         'xdr-insert-cef-alerts',
                         'xdr-isolate-endpoint',
                         'xdr-unisolate-endpoint',
                         'xdr-get-endpoints',
                         'xdr-get-distribution-versions',
                         'xdr-create-distribution',
                         'xdr-get-distribution-url',
                         'xdr-get-create-distribution-status',
                         'xdr-get-audit-management-logs',
                         'xdr-get-audit-agent-reports'],
            "api_modules": "HTTPFeedApiModule",
            "classifiers": "dummy-classifier",
            "incident_types": "dummy-incident-type",
            "indicator_fields": "CommonTypes",
            "indicator_types": "CommonTypes",
            "mappers": [
                "dummy-mapper-in",
                "dummy-mapper-out"
            ]
        }
    }

    # @pytest.mark.skip
    def test_get_integration_data(self):
        """
        Test for getting all the integration data
        """
        # mocker.patch.object('get_pack_name', return_value='DummyPack')
        non_unified_file_path = TESTS_DIR + '/test_files/DummyPack/Integrations/DummyIntegration/DummyIntegration.yml'
        unified_file_path = TESTS_DIR + '/test_files/DummyPack/Integrations/integration-DummyIntegration.yml'

        non_unified_integration_data = get_integration_data(non_unified_file_path)
        unified_integration_data = get_integration_data(unified_file_path)

        test_pairs = [
            (non_unified_integration_data, TestIntegrations.INTEGRATION_DATA),
            (unified_integration_data, TestIntegrations.UNIFIED_INTEGRATION_DATA)
        ]

        for pair in test_pairs:
            returned = pair[0]
            constant = pair[1]

            assert list(returned.keys()) == list(constant.keys())
            const_data = constant.get('Dummy Integration')
            returned_data = returned.get('Dummy Integration')

            for key, value in returned_data.items():
                assert key in const_data.keys()
                if isinstance(value, list):
                    assert sorted(value) == sorted(const_data.get('key'))
                else:
                    assert value == const_data.get(key)


class TestFlow(unittest.TestCase):
    WIDGET_DATA = {
        "id": "temp-widget-dup-check",
        "version": -1,
        "fromVersion": "3.5.0",
        "name": "check duplicate",
        "dataType": "incidents",
        "widgetType": "pie"
    }

    REPORT_DATA = {
        "id": "temp-report-dup-check",
        "name": "Critical and High incidents",
        "description": "All critical and high severity incidents that may need the analyst attention.",
        "fromVersion": "3.5.0"
    }

    CLASSIFIER_DATA = {
        "id": "dup_check-classifier",
        "version": -1,
        "modified": "2018-05-21T12:41:29.542577629Z",
        "defaultIncidentType": "",
        "brandName": "dup_check-classifier-name"
    }

    LAYOUT_DATA = {
        "TypeName": "layout-dup-check-type-name",
        "kind": "details",
        "fromVersion": "5.0.0",
        "layout": {
            "TypeName": "",
            "id": "layout-dup-check-id",
            "kind": "details",
            "modified": "2019-09-01T12:25:49.808989+03:00",
            "name": "",
            "system": False
        },
        "name": "my-layout",
        "typeId": "layout-dup-check-id",
        "version": -1
    }

    DASHBOARD_DATA = {
        "id": "dup-check-dashbaord",
        "version": -1,
        "fromVersion": "4.0.0",
        "description": "",
        "name": "My Dashboard",
    }

    DASHBOARD_DATA2 = {
        "id": "dup-check-dashbaord",
        "version": -1,
        "fromVersion": "4.0.0",
        "description": "",
        "name": "My Dashboard2",
    }

    INCIDENT_FIELD_DATA = {
        "cliName": "accountid",
        "description": "",
        "fieldCalcScript": "",
        "group": 0,
        "id": "incident_account_field_dup_check",
        "name": "Account ID",
        "fromVersion": "5.0.0"
    }

    SCRIPT_DATA = {
        "DummyScript": {
            "name": "DummyScript",
            "file_path": TESTS_DIR + "/test_files/DummyPack/Scripts/DummyScript.yml",
            "fromversion": "5.0.0",
            "tests": [
                "No test - no need to test widget"
            ]
        }
    }

    PLAYBOOK_DATA = {
        "name": "Dummy Playbook",
        "file_path": TESTS_DIR + "/test_files/DummyPack/Playbooks/DummyPlaybook.yml",
        "fromversion": "4.5.0",
        "implementing_scripts": [
            "XDRSyncScript",
            "StopScheduledTask",
        ],
        "implementing_playbooks": [
            "Calculate Severity - Standard",
            "Palo Alto Networks - Malware Remediation",
        ],
        "command_to_integration": {
            "xdr-update-incident": "",
            "autofocus-sample-analysis": ""
        },
        "tests": [
            "No Test"
        ],
        'pack': 'DummyPack',
        "skippable_tasks": [
            "StopScheduledTask",
            "autofocus-sample-analysis"
        ]
    }

    def test_get_script_data(self):
        """
        Test for getting the script data
        """
        file_path = TESTS_DIR + '/test_files/DummyPack/Scripts/DummyScript.yml'
        data = get_script_data(file_path)
        self.assertDictEqual(data, TestFlow.SCRIPT_DATA)

    def test_get_playbook_data(self):
        """
        Test for getting the playbook data
        """
        file_path = TESTS_DIR + '/test_files/DummyPack/Playbooks/DummyPlaybook.yml'
        data = get_playbook_data(file_path)['Dummy Playbook']
        self.assertEqual(data['name'], TestFlow.PLAYBOOK_DATA['name'])
        self.assertEqual(data['file_path'], TestFlow.PLAYBOOK_DATA['file_path'])
        self.assertEqual(data['fromversion'], TestFlow.PLAYBOOK_DATA['fromversion'])
        self.assertListEqual(data['tests'], TestFlow.PLAYBOOK_DATA['tests'])
        self.assertListEqual(data['skippable_tasks'], TestFlow.PLAYBOOK_DATA['skippable_tasks'])
        self.assertSetEqual(set(data['implementing_playbooks']), set(TestFlow.PLAYBOOK_DATA['implementing_playbooks']))
        self.assertListEqual(data['tests'], TestFlow.PLAYBOOK_DATA['tests'])
        self.assertDictEqual(data['command_to_integration'], TestFlow.PLAYBOOK_DATA['command_to_integration'])

    # TODO: unskip
    @pytest.mark.skip
    def test_find_duplicates(self):
        sys.path.insert(1, os.getcwd())
        # Make the script run from tests dir
        os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), TESTS_DIR)))

        # create duplicate report
        temp_report = tempfile.NamedTemporaryFile(mode="w+", prefix='report-',  # disable-secrets-detection
                                                  suffix='.json', dir='Reports')  # disable-secrets-detection
        json.dump(TestFlow.REPORT_DATA, temp_report)
        temp_report.flush()
        os.fsync(temp_report.fileno())
        temp_report2 = tempfile.NamedTemporaryFile(mode="w+", prefix='report-',  # disable-secrets-detection
                                                   suffix='.json', dir='Reports')  # disable-secrets-detection
        json.dump(TestFlow.REPORT_DATA, temp_report2)
        temp_report2.flush()
        os.fsync(temp_report2.fileno())

        # create duplicate Widgets
        temp_widget = tempfile.NamedTemporaryFile(mode="w+", prefix='widget-',  # disable-secrets-detection
                                                  suffix='.json', dir='Widgets')  # disable-secrets-detection
        json.dump(TestFlow.WIDGET_DATA, temp_widget)
        temp_widget.flush()
        os.fsync(temp_widget.fileno())
        temp_widget2 = tempfile.NamedTemporaryFile(mode="w+", prefix='widget-',  # disable-secrets-detection
                                                   suffix='.json', dir='Widgets')  # disable-secrets-detection
        json.dump(TestFlow.WIDGET_DATA, temp_widget2)
        temp_widget2.flush()
        os.fsync(temp_widget2.fileno())

        # create duplicate Classifier
        temp_classifier = tempfile.NamedTemporaryFile(mode="w+", prefix='classifier-',  # disable-secrets-detection
                                                      suffix='.json', dir='Classifiers')  # disable-secrets-detection
        json.dump(TestFlow.WIDGET_DATA, temp_classifier)
        temp_classifier.flush()
        os.fsync(temp_classifier.fileno())
        temp_classifier2 = tempfile.NamedTemporaryFile(mode="w+", prefix='classifier-',  # disable-secrets-detection
                                                       suffix='.json', dir='Classifiers')  # disable-secrets-detection
        json.dump(TestFlow.WIDGET_DATA, temp_classifier2)
        temp_classifier2.flush()
        os.fsync(temp_classifier2.fileno())

        # create duplicate Layout
        temp_layout = tempfile.NamedTemporaryFile(mode="w+", prefix='layout-',  # disable-secrets-detection
                                                  suffix='.json', dir='Layouts')  # disable-secrets-detection
        json.dump(TestFlow.LAYOUT_DATA, temp_layout)
        temp_layout.flush()
        os.fsync(temp_layout.fileno())
        temp_layout2 = tempfile.NamedTemporaryFile(mode="w+", prefix='layout-', suffix='.json',
                                                   # disable-secrets-detection
                                                   dir='Packs/CortexXDR/Layouts')  # disable-secrets-detection
        json.dump(TestFlow.LAYOUT_DATA, temp_layout2)
        temp_layout2.flush()
        os.fsync(temp_layout2.fileno())

        # create duplicate Dashboard
        temp_dashboard = tempfile.NamedTemporaryFile(mode="w+", prefix='dashboard-',  # disable-secrets-detection
                                                     suffix='.json', dir='Dashboards')  # disable-secrets-detection
        json.dump(TestFlow.DASHBOARD_DATA, temp_dashboard)
        temp_dashboard.flush()
        os.fsync(temp_dashboard.fileno())
        temp_dashboard2 = tempfile.NamedTemporaryFile(mode="w+", prefix='dashboard-',  # disable-secrets-detection
                                                      suffix='.json', dir='Dashboards')  # disable-secrets-detection
        json.dump(TestFlow.DASHBOARD_DATA2, temp_dashboard2)
        temp_dashboard2.flush()
        os.fsync(temp_dashboard2.fileno())

        # create one incident type field and one indicator type field with same data
        temp_incident_field = tempfile.NamedTemporaryFile(mode='w+', prefix='incidentfield-',
                                                          # disable-secrets-detection
                                                          suffix='.json',
                                                          dir='IncidentFields')  # disable-secrets-detection
        json.dump(TestFlow.INCIDENT_FIELD_DATA, temp_incident_field)
        temp_incident_field.flush()
        os.fsync(temp_incident_field.fileno())
        temp_indicator_field = tempfile.NamedTemporaryFile(mode='w+', prefix='incidentfield-',
                                                           # disable-secrets-detection
                                                           suffix='.json', dir='IndicatorFields')
        json.dump(TestFlow.INCIDENT_FIELD_DATA, temp_indicator_field)
        temp_indicator_field.flush()
        os.fsync(temp_indicator_field.fileno())

        # create temporary file for id_set
        temp_id_set = tempfile.NamedTemporaryFile(mode="w+", prefix='temp_id_set-',  # disable-secrets-detection
                                                  suffix='.json', dir='Tests/scripts')  # disable-secrets-detection
        json_path = temp_id_set.name

        re_create_id_set(json_path, ['Reports', 'Layouts', 'Widgets', 'Classifiers', 'Dashboards',
                                     'IndicatorFields', 'IncidentFields'])
        with open(json_path) as json_file:
            data = json.load(json_file)
            dup_data = find_duplicates(data)
            assert any('temp-widget-dup-check' in i for i in dup_data)
            assert any('temp-report-dup-check' in i for i in dup_data)
            assert any('temp-widget-dup-check' in i for i in dup_data)
            assert any('dup-check-dashbaord' in i for i in dup_data)
            assert any('layout-dup-check-id' in i for i in dup_data)
            assert any('incident_account_field_dup_check' in i for i in dup_data)


if __name__ == '__main__':
    unittest.main()
