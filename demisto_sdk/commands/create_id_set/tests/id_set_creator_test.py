import os
import shutil
from tempfile import mkdtemp

import pytest
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.update_id_set import (get_layout_data,
                                                       has_duplicate)
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
        - An layout file called layout-to-test.json

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
