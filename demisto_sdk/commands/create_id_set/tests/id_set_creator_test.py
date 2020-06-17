import os
import shutil
from tempfile import mkdtemp

import pytest
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.update_id_set import (
    get_incident_field_data, get_incident_type_data, get_layout_data,
    get_values_for_keys_recursively, has_duplicate)
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator


class TestIDSetCreator:
    def setup(self):
        tests_dir = f'{git_path()}/demisto_sdk/tests'
        self.id_set_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example', 'id_set.json')
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


INPUT_TEST_HAS_DUPLICATE = [
    ('Access', False),
    ('urlRep', True)
]

ID_SET = [
    {'Access': {'typeID': 'Access', 'kind': 'edit', 'path': 'Layouts/layout-edit-Access.json'}},
    {'Access': {'typeID': 'Access', 'fromversion': '4.1.0', 'kind': 'details', 'path': 'layout-Access.json'}},
    {'urlRep': {'typeID': 'urlRep', 'kind': 'Details', 'path': 'Layouts/layout-Details-url.json'}},
    {'urlRep': {'typeID': 'urlRep', 'fromversion': '5.0.0', 'kind': 'Details', 'path': 'layout-Details-url_5.4.9.json'}}
]


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
    result = has_duplicate(ID_SET, list_input, 'Layouts', False)
    assert list_output == result


def test_get_layout_data():
    """
    Given
        - A layout file called layout-to-test.json

    When
        - parsing layout files

    Then
        - parsing all the data from file successfully
    """
    test_dir = f'{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/layout-to-test.json'
    result = get_layout_data(test_dir)
    result = result.get('urlRep')
    assert 'kind' in result.keys()
    assert 'name' in result.keys()
    assert 'fromversion' in result.keys()
    assert 'toversion' in result.keys()
    assert 'path' in result.keys()
    assert 'typeID' in result.keys()
    assert 'incident_and_indicator_types' in result.keys()
    assert 'incident_and_indicator_fields' in result.keys()


def test_get_layout_data_no_incident_types_and_fields():
    """
    Given
        - A layout file called layout-to-test.json that doesnt have related incident fields and indicator fields

    When
        - parsing layout files

    Then
        - parsing all the data from file successfully
    """
    test_dir = f'{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/layout-to-test-no-types-fields.json'
    result = get_layout_data(test_dir)
    result = result.get('urlRep')
    assert 'kind' in result.keys()
    assert 'name' in result.keys()
    assert 'fromversion' in result.keys()
    assert 'toversion' in result.keys()
    assert 'path' in result.keys()
    assert 'typeID' in result.keys()
    assert 'incident_and_indicator_types' in result.keys()
    assert 'incident_and_indicator_fields' not in result.keys()


def test_get_incident_fields_data():
    """
    Given
        - An incident field file called incidentfield-to-test.json

    When
        - parsing incident field files

    Then
        - parsing all the data from file successfully
    """
    test_dir = f'{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/incidentfield-to-test.json'
    result = get_incident_field_data(test_dir, [])
    result = result.get('incidentfield-test')
    assert 'name' in result.keys()
    assert 'fromversion' in result.keys()
    assert 'toversion' in result.keys()
    assert 'incident_types' in result.keys()
    assert 'scripts' in result.keys()


def test_get_incident_fields_data_no_types_scripts():
    """
    Given
        - An incident field file called incidentfield-to-test-no-types_scripts.json with no script or incident type
        related to it

    When
        - parsing incident field files

    Then
        - parsing all the data from file successfully
    """
    test_dir = \
        f'{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/incidentfield-to-test-no-types_scripts.json'
    result = get_incident_field_data(test_dir, [])
    result = result.get('incidentfield-test')
    assert 'name' in result.keys()
    assert 'fromversion' in result.keys()
    assert 'toversion' in result.keys()
    assert 'incident_types' not in result.keys()
    assert 'scripts' not in result.keys()


def test_get_incident_types_data():
    """
    Given
        - An incident type file called incidenttype-to-test.json

    When
        - parsing incident type files

    Then
        - parsing all the data from file successfully
    """
    test_dir = f'{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/incidenttype-to-test.json'
    result = get_incident_type_data(test_dir)
    result = result.get('dummy incident type')
    assert 'name' in result.keys()
    assert 'fromversion' in result.keys()
    assert 'playbooks' in result.keys()
    assert 'scripts' in result.keys()


def test_get_incident_types_data_no_playbooks_scripts():
    """
    Given
        - An incident type file called incidenttype-to-test-no-playbook-script.json with no script or playbook
        related to it

    When
        - parsing incident type files

    Then
        - parsing all the data from file successfully
    """
    test_dir = \
        f'{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/incidenttype-to-test-no-playbook-script.json'
    result = get_incident_type_data(test_dir)
    result = result.get('dummy incident type')
    assert 'name' in result.keys()
    assert 'fromversion' in result.keys()
    assert 'playbooks' not in result.keys()
    assert 'scripts' not in result.keys()


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
