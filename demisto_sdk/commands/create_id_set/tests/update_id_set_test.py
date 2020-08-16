import json
import os
import shutil
import sys
import tempfile
import unittest
from tempfile import mkdtemp

import pytest
from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.update_id_set import (
    find_duplicates, get_classifier_data, get_fields_by_script_argument,
    get_general_data, get_incident_fields_by_playbook_input,
    get_incident_type_data, get_indicator_type_data, get_layout_data,
    get_layoutscontainer_data, get_mapper_data, get_playbook_data,
    get_script_data, get_values_for_keys_recursively, has_duplicate,
    process_general_items, process_incident_fields, process_integration,
    process_script, re_create_id_set)
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from TestSuite.utils import IsEqualFunctions

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

    def test_create_id_set_no_output(self, mocker):
        import demisto_sdk.commands.common.update_id_set as uis
        mocker.patch.object(uis, 'cpu_count', return_value=1)
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

    def test_process_integration__sanity(self):
        """
        Given
            - A valid script package folder located at Packs/DummyPack/Scripts/DummyScript.

        When
            - parsing script files

        Then
            - integration data will be collected properly
        """
        non_unified_file_path = os.path.join(TESTS_DIR, 'test_files',
                                             'DummyPack', 'Integrations', 'DummyIntegration')

        res = process_integration(non_unified_file_path, True)
        assert len(res) == 1
        non_unified_integration_data = res[0]

        unified_file_path = os.path.join(TESTS_DIR, 'test_files',
                                         'DummyPack', 'Integrations', 'integration-DummyIntegration.yml')

        res = process_integration(unified_file_path, True)
        assert len(res) == 1
        unified_integration_data = res[0]

        test_pairs = [
            (non_unified_integration_data, TestIntegrations.INTEGRATION_DATA),
            (unified_integration_data, TestIntegrations.UNIFIED_INTEGRATION_DATA)
        ]

        for returned, constant in test_pairs:

            assert IsEqualFunctions.is_lists_equal(list(returned.keys()), list(constant.keys()))

            const_data = constant.get('Dummy Integration')
            returned_data = returned.get('Dummy Integration')

            assert IsEqualFunctions.is_dicts_equal(returned_data, const_data)

    @staticmethod
    def test_process_integration__exception():
        """
        Given
            - An invalid "integration" file located at invalid_file_structures where commonfields object is not a dict.

        When
            - parsing integration files

        Then
            - an exception will be raised
        """
        test_file_path = os.path.join(TESTS_DIR, 'test_files', 'invalid_file_structures', 'integration.yml')
        with pytest.raises(Exception):
            process_integration(test_file_path, True)


class TestScripts:
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

    PACK_SCRIPT_DATA = {
        "DummyScript": {
            "name": "DummyScript",
            "file_path": TESTS_DIR + "/test_files/Packs/DummyPack/Scripts/DummyScript/DummyScript.yml",
        }
    }

    @staticmethod
    def test_get_script_data():
        """
        Test for getting the script data
        """
        file_path = TESTS_DIR + '/test_files/DummyPack/Scripts/DummyScript.yml'
        data = get_script_data(file_path)

        assert IsEqualFunctions.is_lists_equal(list(data.keys()), list(TestScripts.SCRIPT_DATA.keys()))

        const_data = TestScripts.SCRIPT_DATA.get('DummyScript')
        returned_data = data.get('DummyScript')

        assert IsEqualFunctions.is_dicts_equal(returned_data, const_data)

    @staticmethod
    def test_process_script__sanity_package():
        """
        Given
            - An invalid "script" file located at invalid_file_structures where commonfields object is not a dict.

        When
            - parsing script files

        Then
            - an exception will be raised
        """
        test_file_path = os.path.join(TESTS_DIR, 'test_files',
                                      'Packs', 'DummyPack', 'Scripts', 'DummyScript')
        res = process_script(test_file_path, True)
        assert len(res) == 1
        data = res[0]

        assert IsEqualFunctions.is_lists_equal(list(data.keys()), list(TestScripts.PACK_SCRIPT_DATA.keys()))

        const_data = TestScripts.PACK_SCRIPT_DATA.get('DummyScript')
        returned_data = data.get('DummyScript')

        assert IsEqualFunctions.is_dicts_equal(returned_data, const_data)

    @staticmethod
    def test_process_script__exception():
        """
        Given
            - An invalid "script" file located at invalid_file_structures where commonfields object is not a dict.

        When
            - parsing script files

        Then
            - an exception will be raised
        """
        test_file_path = os.path.join(TESTS_DIR, 'test_files', 'invalid_file_structures', 'script.yml')
        with pytest.raises(Exception):
            process_script(test_file_path, True)


class TestPlaybooks:
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
        "skippable_tasks": [
            "StopScheduledTask",
            "autofocus-sample-analysis"
        ]
    }

    @staticmethod
    def test_get_playbook_data():
        """
        Test for getting the playbook data
        """
        file_path = TESTS_DIR + '/test_files/DummyPack/Playbooks/DummyPlaybook.yml'
        data = get_playbook_data(file_path)['Dummy Playbook']

        assert IsEqualFunctions.is_dicts_equal(data, TestPlaybooks.PLAYBOOK_DATA)

    @staticmethod
    def test_get_playbook_data_2():
        """
        Given
            - A playbook file called playbook-with-incident-fields.yml

        When
            - parsing playbook files

        Then
            - parsing all the data from file successfully
        """
        test_dir = f'{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/playbook-with-incident-fields.yml'
        result = get_playbook_data(test_dir)
        result = result.get('Arcsight - Get events related to the Case')
        assert 'name' in result.keys()
        assert 'file_path' in result.keys()
        assert 'implementing_scripts' in result.keys()
        assert 'command_to_integration' in result.keys()
        assert 'tests' in result.keys()
        assert 'incident_fields' in result.keys()
        assert 'indicator_fields' in result.keys()

    @staticmethod
    def test_get_playbook_data_no_fields():
        """
        Given
            - A playbook file called playbook-no-incident-fields.yml without any
                incident or indicator fields that it depends on.

        When
            - parsing playbook files

        Then
            - parsing all the data from file successfully
        """
        test_dir = f'{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/playbook-no-incident-fields.yml'
        result = get_playbook_data(test_dir)
        result = result.get('Arcsight - Get events related to the Case')
        assert 'name' in result.keys()
        assert 'file_path' in result.keys()
        assert 'implementing_scripts' in result.keys()
        assert 'command_to_integration' in result.keys()
        assert 'tests' in result.keys()
        assert 'incident_fields' not in result.keys()
        assert 'indicator_fields' not in result.keys()

    @staticmethod
    def test_process_playbook__exception():
        """
        Given
            - An invalid "playbook" file located at invalid_file_structures where tasks object is not a dict.

        When
            - parsing playbook files

        Then
            - an exception will be raised
        """
        test_file_path = os.path.join(TESTS_DIR, 'test_files', 'invalid_file_structures', 'playbook.yml')
        with pytest.raises(Exception):
            process_general_items(test_file_path, True, (FileType.PLAYBOOK,), get_playbook_data)

    @staticmethod
    def test_get_playbook_data_bad_graph():
        """
        Given
            - A playbook file called playbook-invalid-bad-graph.yml:
                - task 1 point to non-existing task
                - task 2 is not connected

        When
            - parsing playbook files

        Then
            - parsing flow graph from file successfully (only tasks 0 and 1 will be in the graph)
        """
        test_file_path = os.path.join(TESTS_DIR, 'test_files', 'playbook-invalid-bad-graph.yml')
        result = get_playbook_data(test_file_path)
        playbook_data = result.get('InvalidPlaybook-BadGraph', {})
        assert playbook_data.get('name') == 'InvalidPlaybook-BadGraph'
        assert playbook_data.get('command_to_integration', {}).get('ip') == ''
        assert playbook_data.get('command_to_integration', {}).get('domain') == ''
        assert 'domain' in playbook_data.get('skippable_tasks', [])
        assert 'ip' not in playbook_data.get('skippable_tasks', [])

    @staticmethod
    def test_get_playbook_data_bad_graph_2():
        """
        Given
            - A playbook file called playbook-invalid-bad-graph_2.yml:
                - starttaskid=5 but task 5 does not exist

        When
            - parsing playbook files

        Then
            - parsing flow graph from file successfully (no actual tasks will be in the graph)
        """
        test_file_path = os.path.join(TESTS_DIR, 'test_files', 'playbook-invalid-bad-graph_2.yml')
        result = get_playbook_data(test_file_path)
        playbook_data = result.get('InvalidPlaybook-BadGraph', {})
        assert playbook_data.get('name') == 'InvalidPlaybook-BadGraph'
        assert playbook_data.get('command_to_integration', {}).get('ip') == ''
        assert playbook_data.get('command_to_integration', {}).get('domain') == ''
        # domain task is marked as skippable so it will be included regardless to the graph.
        assert 'domain' in playbook_data.get('skippable_tasks', [])
        assert len(playbook_data.get('skippable_tasks', [])) == 1


class TestLayouts:
    @staticmethod
    def test_process_layouts__sanity():
        """
        Given
            - A layout file called layout-to-test.json

        When
            - parsing layout files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(git_path(), 'demisto_sdk', 'commands', 'create_id_set', 'tests',
                                 'test_data', 'layout-to-test.json')
        res = process_general_items(test_file, True, (FileType.LAYOUT,), get_layout_data)
        assert len(res) == 1
        result = res[0]
        result = result.get('urlRep')
        assert 'kind' in result.keys()
        assert 'name' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'toversion' in result.keys()
        assert 'file_path' in result.keys()
        assert 'typeID' in result.keys()
        assert 'incident_and_indicator_types' in result.keys()
        assert 'incident_and_indicator_fields' in result.keys()

    @staticmethod
    def test_process_layouts__no_incident_types_and_fields():
        """
        Given
            - A layout file called layout-to-test.json that doesnt have related incident fields and indicator fields

        When
            - parsing layout files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(git_path(), 'demisto_sdk', 'commands', 'create_id_set', 'tests',
                                 'test_data', 'layout-to-test-no-types-fields.json')

        res = process_general_items(test_file, False, (FileType.LAYOUT,), get_layout_data)
        assert len(res) == 1
        result = res[0]
        result = result.get('urlRep')
        assert 'kind' in result.keys()
        assert 'name' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'toversion' in result.keys()
        assert 'file_path' in result.keys()
        assert 'typeID' in result.keys()
        assert 'incident_and_indicator_types' in result.keys()
        assert 'incident_and_indicator_fields' not in result.keys()

    @staticmethod
    def test_process_layoutscontainer__sanity():
        """
        Given
            - A layoutscontainer file called layoutscontainer-to-test.json
        When
            - parsing layoutscontainer files
        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(git_path(), 'demisto_sdk', 'commands', 'create_id_set', 'tests',
                                 'test_data', 'layoutscontainer-to-test.json')

        res = process_general_items(test_file, True, (FileType.LAYOUTS_CONTAINER,), get_layoutscontainer_data)
        assert len(res) == 1
        result = res[0]
        result = result.get('layouts_container_test')
        assert 'detailsV2' in result.keys()
        assert 'name' in result.keys()
        assert 'group' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'toversion' in result.keys()
        assert 'file_path' in result.keys()
        assert 'incident_and_indicator_types' in result.keys()
        assert 'incident_and_indicator_fields' in result.keys()


class TestIncidentFields:
    @staticmethod
    def test_process_incident_fields__sanity():
        """
        Given
            - An incident field file called incidentfield-to-test.json

        When
            - parsing incident field files

        Then
            - parsing all the data from file successfully
        """
        test_dir = os.path.join(git_path(), 'demisto_sdk', 'commands', 'create_id_set', 'tests',
                                'test_data', 'incidentfield-to-test.json')
        res = process_incident_fields(test_dir, True, [])
        assert len(res) == 1
        result = res[0]
        result = result.get('incidentfield-test')
        assert 'name' in result.keys()
        assert 'file_path' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'toversion' in result.keys()
        assert 'incident_types' in result.keys()
        assert 'scripts' in result.keys()

    @staticmethod
    def test_process_incident_fields__no_types_scripts():
        """
        Given
            - An incident field file called incidentfield-to-test-no-types_scripts.json with no script or incident type
            related to it

        When
            - parsing incident field files

        Then
            - parsing all the data from file successfully
        """
        test_dir = os.path.join(git_path(), 'demisto_sdk', 'commands', 'create_id_set', 'tests',
                                'test_data', 'incidentfield-to-test-no-types_scripts.json')
        res = process_incident_fields(test_dir, True, [])
        assert len(res) == 1
        result = res[0]
        result = result.get('incidentfield-test')
        assert 'name' in result.keys()
        assert 'file_path' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'toversion' in result.keys()
        assert 'incident_types' not in result.keys()
        assert 'scripts' not in result.keys()


class TestIndicatorType:
    @staticmethod
    def test_process_indicator_type__sanity():
        """
        Given
            - An indicator type file called reputation-indicatortype.json.

        When
            - parsing indicator type files

        Then
            - parsing all the data from file successfully
        """
        test_dir = f'{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/reputation-indicatortype.json'

        result = get_indicator_type_data(test_dir, [{'integration': {'commands': ['ip']}}])
        result = result.get('indicator-type-dummy')
        assert 'name' in result.keys()
        assert 'file_path' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'integrations' in result.keys()
        assert 'scripts' in result.keys()
        assert "dummy-script" in result.get('scripts')
        assert "dummy-script-2" in result.get('scripts')
        assert "dummy-script-3" in result.get('scripts')

    @staticmethod
    def test_get_indicator_type_data_no_integration_no_scripts():
        """
        Given
            - An indicator type file called reputation-indicatortype_no_script_no_integration.json without any
                integrations or scripts that it depends on.

        When
            - parsing indicator type files

        Then
            - parsing all the data from file successfully
        """
        test_dir = f'{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/' \
                   f'reputation-indicatortype_no_script_no_integration.json'

        result = get_indicator_type_data(test_dir, [])
        result = result.get('indicator-type-dummy')
        assert 'name' in result.keys()
        assert 'file_path' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'integrations' not in result.keys()
        assert 'scripts' not in result.keys()


class TestIncidentTypes:
    @staticmethod
    def test_get_incident_type_data__sanity():
        """
        Given
            - An incident type file called incidenttype-to-test.json

        When
            - parsing incident type files

        Then
            - parsing all the data from file successfully
        """
        test_file = f'{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/incidenttype-to-test.json'

        res = get_incident_type_data(test_file)
        result = res.get('dummy incident type')
        assert 'name' in result.keys()
        assert 'file_path' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'playbooks' in result.keys()
        assert 'scripts' in result.keys()

    @staticmethod
    def test_get_incident_type_data__no_playbooks_scripts():
        """
        Given
            - An incident type file called incidenttype-to-test-no-playbook-script.json with no script or playbook
            related to it

        When
            - parsing incident type files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(git_path(), 'demisto_sdk', 'commands', 'create_id_set',
                                 'tests', 'test_data', 'incidenttype-to-test-no-playbook-script.json')

        res = get_incident_type_data(test_file)
        result = res.get('dummy incident type')
        assert 'name' in result.keys()
        assert 'file_path' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'playbooks' not in result.keys()
        assert 'scripts' not in result.keys()


class TestClassifiers:
    @staticmethod
    def test_process_classifiers__no_types_scripts():
        """
        Given
            - An classifier file called classifier-to-test-no-incidenttypes.json with incident type
            related to it

        When
            - parsing classifier files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(git_path(), 'demisto_sdk', 'commands', 'create_id_set', 'tests',
                                 'test_data', 'classifier-to-test-no-incidenttypes.json')

        res = get_classifier_data(test_file)
        result = res.get('dummy classifier')
        assert 'name' in result.keys()
        assert 'file_path' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'incident_types' not in result.keys()
        assert 'incident_fields' not in result.keys()


class TestMappers:
    @staticmethod
    def test_process_mappers__sanity():
        """
        Given
            - A mapper file called classifier-mapper-to-test.json

        When
            - parsing mapper files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(git_path(), 'demisto_sdk', 'commands', 'create_id_set', 'tests',
                                 'test_data', 'classifier-mapper-to-test.json')

        res = get_mapper_data(test_file)
        result = res.get('dummy mapper')
        assert 'name' in result.keys()
        assert 'file_path' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'incident_types' in result.keys()
        assert 'incident_fields' in result.keys()
        assert 'dummy incident type' in result['incident_types']
        assert 'dummy incident type 1' in result['incident_types']
        assert 'dummy incident type 2' in result['incident_types']
        assert 'dummy incident field' in result['incident_fields']
        assert 'dummy incident field 1' in result['incident_fields']
        assert 'dummy incident field 2' in result['incident_fields']
        assert 'dummy incident field 3' in result['incident_fields']
        assert 'occurred' not in result['incident_fields']

    @staticmethod
    def test_process_mappers__no_types_fields():
        """
        Given
            - An mapper file called classifier-mapper-to-test-no-types-fields.json with incident type
            related to it

        When
            - parsing mapper files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(git_path(), 'demisto_sdk', 'commands', 'create_id_set', 'tests',
                                 'test_data', 'classifier-mapper-to-test-no-types-fields.json')

        res = get_mapper_data(test_file)
        result = res.get('dummy mapper')
        assert 'name' in result.keys()
        assert 'file_path' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'incident_types' not in result.keys()
        assert 'incident_fields' not in result.keys()


class TestGenericFunctions:
    @staticmethod
    def test_process_general_items__sanity():
        """
        Given
            - A classifier file called classifier-to-test.json

        When
            - parsing classifier files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(git_path(), 'demisto_sdk', 'commands', 'create_id_set', 'tests',
                                 'test_data', 'classifier-to-test.json')

        res = process_general_items(test_file, True, (FileType.CLASSIFIER,), get_classifier_data)
        assert len(res) == 1
        result = res[0]
        result = result.get('dummy classifier')
        assert 'name' in result.keys()
        assert 'file_path' in result.keys()
        assert 'fromversion' in result.keys()
        assert 'incident_types' in result.keys()
        assert 'dummy incident type' in result['incident_types']
        assert 'dummy incident type 2' in result['incident_types']
        assert 'dummy incident type 3' in result['incident_types']

    @staticmethod
    def test_process_general_items__exception():
        """
        Given
            - An invalid "dashboard" file located at invalid_file_structures where id is a list so it can't be used
                as a dict key.

        When
            - parsing dashboard files

        Then
            - an exception will be raised
        """
        test_file_path = os.path.join(TESTS_DIR, 'test_files', 'invalid_file_structures', 'dashboard.json')
        with pytest.raises(Exception):
            process_general_items(test_file_path, True, (FileType.DASHBOARD,), get_general_data)

    @staticmethod
    def test_get_values_for_keys_recursively():
        """
        Given
            - A list of keys to extract their values from a dict

        When
            - Extracting data from nested elements in the json

        Then
            - Extracting the values from all the levels of nesting in the json
        """

        test_dict = {
            'id': 1,
            'nested': {
                'x1': 1,
                'x2': 'x2',
                'x3': False,
                'x4': [
                    {
                        'x1': 2,
                        'x2': 55
                    },
                    {
                        'x3': 1,
                        'x2': True
                    }
                ]
            },
            'x2': 4.0
        }

        test_keys = ['x1', 'x2', 'x3']

        expected = {
            'x1': [1, 2],
            'x2': ['x2', 55, True, 4.0],
            'x3': [False, 1]
        }

        assert expected == get_values_for_keys_recursively(test_dict, test_keys)

    INPUT_WITH_INCIDENT_FIELD_SIMPLE = {
        "key": "AlertID",
        "value": {
            "simple": "${incident.field_name}"
        },
        "required": False
    }

    INPUT_WITH_INCIDENT_FIELD_COMPLEX1 = {
        "key": "AlertID",
        "value": {
            "complex": {
                "root": "incident",
                "accessor": "field_name"
            }
        },
        "required": False
    }

    INPUT_WITH_INCIDENT_FIELD_COMPLEX2 = {
        "key": "AlertID",
        "value": {
            "complex": {
                "root": "incident.field_name",
                "accessor": "username"
            }
        },
        "required": False
    }

    INPUT_SIMPLE_WITHOUT_INCIDENT_FIELD = {
        "key": "AlertID",
        "value": {
            "simple": "${not_incident.field_name}"
        },
        "required": False
    }

    INPUT_COMPLEX_WITHOUT_INCIDENT_FIELD = {
        "key": "AlertID",
        "value": {
            "complex": {
                "root": "something",
                "accessor": "username"
            }
        },
        "required": False
    }

    INPUTS = [
        (INPUT_WITH_INCIDENT_FIELD_SIMPLE, True),
        (INPUT_WITH_INCIDENT_FIELD_COMPLEX1, True),
        (INPUT_WITH_INCIDENT_FIELD_COMPLEX2, True),
        (INPUT_SIMPLE_WITHOUT_INCIDENT_FIELD, False),
        (INPUT_COMPLEX_WITHOUT_INCIDENT_FIELD, False)
    ]

    @staticmethod
    @pytest.mark.parametrize('playbook_input, are_there_incident_fields', INPUTS)
    def test_get_incident_fields_by_playbook_input(playbook_input, are_there_incident_fields):
        """
        Given
            - A list of playbook inputs

        When
            - Searching for dependent incident fields

        Then
            -  Finding all dependent incident fields in the input
        """

        result = get_incident_fields_by_playbook_input(playbook_input.get('value'))
        if are_there_incident_fields:
            assert "field_name" in result
        else:
            assert result == set()

    EXAMPLE_TASK_WITH_SIMPLE_SCRIPT_ARGUMENTS = {
        "id": "ID",
        "scriptarguments": {
            "field_name": {
                "simple": "${inputs.IndicatorTagName}"
            }
        }
    }

    EXAMPLE_TASK_WITH_CUSTOM_FIELDS_SCRIPT_ARGUMENTS = {
        "id": "ID",
        "scriptarguments": {
            "customFields": {
                "simple": '[{"field_name":"${inputs.IndicatorTagName}"}]'
            }
        }
    }

    TASK_INPUTS = [
        # EXAMPLE_TASK_WITH_SIMPLE_SCRIPT_ARGUMENTS,
        EXAMPLE_TASK_WITH_CUSTOM_FIELDS_SCRIPT_ARGUMENTS
    ]

    @staticmethod
    @pytest.mark.parametrize('task', TASK_INPUTS)
    def test_get_fields_by_script_argument(task):
        """
        Given
            - A list of playbook tasks

        When
            - Searching for dependent incident fields in the task script arguments

        Then
            - Finding all dependent incident fields in the task
        """

        result = get_fields_by_script_argument(task)
        assert "field_name" in result


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
