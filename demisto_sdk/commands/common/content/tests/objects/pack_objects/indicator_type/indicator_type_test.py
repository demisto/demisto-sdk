import pytest
from demisto_sdk.commands.common.content.objects.pack_objects import (
    IndicatorType, OldIndicatorType)
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import \
    REPUTATION

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'


def mock_indicator_type(repo, indicator_type_data=None):
    pack = repo.create_pack('Temp')
    return pack.create_indicator_type(name='MyIndicatorType', content=indicator_type_data if
                                      indicator_type_data else REPUTATION)


class TestIndicatorType:
    def test_objects_factory(self, repo):
        indicator_type = mock_indicator_type(repo)
        obj = path_to_pack_object(indicator_type.path)
        assert isinstance(obj, IndicatorType)

    def test_prefix(self, repo):
        indicator_type = mock_indicator_type(repo)
        obj = IndicatorType(indicator_type.path)
        assert obj.normalize_file_name() == indicator_type.name

    data_is_valid_version = [
        (-1, True),
        (0, False),
        (1, False),
    ]

    @pytest.mark.parametrize('version, is_valid', data_is_valid_version)
    def test_is_valid_version(self, version, is_valid, repo):
        indicator_type_data = REPUTATION.copy()
        indicator_type_data['version'] = version
        indicator_type = mock_indicator_type(repo, indicator_type_data)
        indicator_type_obj = IndicatorType(indicator_type.path)
        assert indicator_type_obj.is_valid_version() == is_valid, f'is_valid_version({version}) returns {not is_valid}.'

    data_is_valid_expiration = [
        (0, True),
        (500, True),
        (-1, False),
        ("not_valid", False)
    ]

    @pytest.mark.parametrize('expiration, is_valid', data_is_valid_expiration)
    def test_is_valid_expiration(self, expiration, is_valid, repo):
        indicator_type_data = REPUTATION.copy()
        indicator_type_data['fromVersion'] = "5.5.0"
        indicator_type_data['expiration'] = expiration
        indicator_type = mock_indicator_type(repo, indicator_type_data)
        indicator_type_obj = IndicatorType(indicator_type.path)
        assert indicator_type_obj.is_valid_expiration() == is_valid, f'is_valid_expiration({expiration})' \
                                                                     f' returns {not is_valid}.'

    data_is_id_equals_details = [
        ("CIDR", "CIDR", True),
        ("CIDR", "CIDR2", False)
    ]

    @pytest.mark.parametrize('id_, details, is_valid', data_is_id_equals_details)
    def test_is_id_equals_details(self, id_, details, is_valid, repo):
        indicator_type_data = REPUTATION.copy()
        indicator_type_data['id'] = id_
        indicator_type_data['details'] = details
        indicator_type = mock_indicator_type(repo, indicator_type_data)
        indicator_type_obj = IndicatorType(indicator_type.path)
        assert indicator_type_obj.is_id_equals_details() == is_valid, f'is_id_equals_details({id_}, {details})' \
                                                                      f' returns {not is_valid}.'

    data_is_valid_id = [
        ("CIDR", True),
        ("host_test", True),
        ("ipv4&ipv6", True),
        ("ipv4 ipv6", True),
        ("ipv4-ipv6", False),
        ("ipv4*ipv6", False),
    ]

    @pytest.mark.parametrize('id_, is_valid', data_is_valid_id)
    def test_is_valid_id_field(self, id_, is_valid, repo):
        indicator_type_data = REPUTATION.copy()
        indicator_type_data['id'] = id_
        indicator_type = mock_indicator_type(repo, indicator_type_data)
        indicator_type_obj = IndicatorType(indicator_type.path)
        assert indicator_type_obj.is_valid_indicator_type_id() == is_valid

    data_is_empty_id_and_details = [
        ("CIDR", "CIDR", True),
        ("CIDR", "", False),
        ("", "CIDR", False),
    ]

    @pytest.mark.parametrize('id_, details, is_valid', data_is_empty_id_and_details)
    def test_is_id_and_details_empty(self, id_, details, is_valid, repo):
        indicator_type_data = REPUTATION.copy()
        indicator_type_data['id'] = id_
        indicator_type_data['details'] = details
        indicator_type = mock_indicator_type(repo, indicator_type_data)
        indicator_type_obj = IndicatorType(indicator_type.path)
        assert indicator_type_obj.is_required_fields_empty() == is_valid


class TestOldIndicatorType:
    @pytest.mark.parametrize(argnames="file", argvalues=["reputations.json"])
    def test_objects_factory(self, datadir, file: str):
        obj = path_to_pack_object(datadir[file])
        assert isinstance(obj, OldIndicatorType)

    @pytest.mark.parametrize(argnames="file", argvalues=["reputations.json"])
    def test_prefix(self, datadir, file: str):
        obj = OldIndicatorType(datadir[file])
        assert obj.normalize_file_name() == "reputations.json"
