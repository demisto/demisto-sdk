import pytest
from demisto_sdk.commands.common.content.objects.pack_objects import Dashboard
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import \
    DASHBOARD

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
BASE_VALIDATOR = BaseValidator()


def mock_valid_dashboard(repo, dashboard_data=None):
    pack = repo.create_pack('Temp')
    return pack.create_dashboard(name="myDashboard", content=dashboard_data if dashboard_data else DASHBOARD)


def test_objects_factory(repo):
    dashboard = mock_valid_dashboard(repo)
    obj = path_to_pack_object(dashboard.path)
    assert isinstance(obj, Dashboard)


def test_prefix(repo):
    dashboard = mock_valid_dashboard(repo)
    obj = Dashboard(dashboard.path)
    assert obj.normalize_file_name() == dashboard.name


data_is_valid_version = [
    (-1, True),
    (0, False),
    (1, False),
]


@pytest.mark.parametrize('version, is_valid', data_is_valid_version)
def test_is_valid_version(version, is_valid, repo):
    dashboard_data = DASHBOARD.copy()
    dashboard_data['version'] = version
    dashboard = mock_valid_dashboard(repo, dashboard_data)
    dashboard_obj = Dashboard(dashboard.path, BASE_VALIDATOR)
    assert dashboard_obj.is_valid_version() == is_valid, f'is_valid_version({version}) returns {not is_valid}.'


data_is_id_equal_name = [
    ('aa', 'aa', True),
    ('aa', 'ab', False),
    ('my-home-dashboard', 'My Dashboard', False)
]


@pytest.mark.parametrize('id_, name, is_valid', data_is_id_equal_name)
def test_is_id_equal_name(id_, name, is_valid, repo):
    dashboard_data = DASHBOARD.copy()
    dashboard_data['id'] = id_
    dashboard_data['name'] = name
    dashboard = mock_valid_dashboard(repo, dashboard_data)
    dashboard_obj = Dashboard(dashboard.path, BASE_VALIDATOR)
    assert dashboard_obj.is_id_equals_name() == is_valid, f'is_id_equal_name returns {not is_valid}.'


data_contains_forbidden_fields = [
    ({"system": False}, False),
    ({"isCommon": False}, False),
    ({"shared": False}, False),
    ({"owner": "Admin"}, False),
    ({"layout": [{"widget": {"owner": "Admin"}}]}, False),
    ({"layout": [{"widget": {"shared": "False"}}]}, False),
    ({"layout": [{"widget": {"shared4": "False"}}]}, True)
]


@pytest.mark.parametrize('current_file, is_valid', data_contains_forbidden_fields)
def test_contains_forbidden_fields(current_file, is_valid, repo):
    dashboard_data = DASHBOARD.copy()
    for key, val in current_file.items():
        dashboard_data[key] = val
    dashboard = mock_valid_dashboard(repo, dashboard_data)
    dashboard_obj = Dashboard(dashboard.path, BASE_VALIDATOR)
    assert dashboard_obj.contains_forbidden_fields() == is_valid, f'is_excluding_fields returns {not is_valid}.'


data_is_including_fields = [
    ({"fromDate": "1", "toDate": "2", "fromDateLicense": "3"}, True),
    ({"fromDate": "1", "toDate": "2", "fromDateLicense": "3",
      "layout": [{"widget": {"fromDate": "1", "toDate": "2", "fromDateLicense": "3"}}]}, True),
    ({"fromDate": "1", "toDate": "2", "fromDateLicense": "3",
      "layout": [{"widget": {"name": "bla", "fromDate": "1", "fromDateLicense": "3"}}]}, False)
]


@pytest.mark.parametrize('current_file, is_valid', data_is_including_fields)
def test_is_including_fields(current_file, is_valid, repo):
    dashboard_data = DASHBOARD.copy()
    for key, val in current_file.items():
        dashboard_data[key] = val
    dashboard = mock_valid_dashboard(repo, dashboard_data)
    dashboard_obj = Dashboard(dashboard.path, BASE_VALIDATOR)
    assert dashboard_obj.is_including_fields() == is_valid, f'is_including_fields returns {not is_valid}.'
