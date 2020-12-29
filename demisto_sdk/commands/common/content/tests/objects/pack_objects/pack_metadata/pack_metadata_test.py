from datetime import datetime

import pytest
from demisto_sdk.commands.common.constants import (PACKS_DIR, XSOAR_AUTHOR,
                                                   XSOAR_SUPPORT,
                                                   XSOAR_SUPPORT_URL)
from demisto_sdk.commands.common.content.objects.pack_objects import \
    PackMetaData
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
PACK_METADATA = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / 'pack_metadata.json'


def test_objects_factory():
    obj = path_to_pack_object(PACK_METADATA)
    assert isinstance(obj, PackMetaData)


def test_prefix():
    obj = PackMetaData(PACK_METADATA)
    assert obj.normalize_file_name() == PACK_METADATA.name


def test_created_setter_bad_string_data():
    obj = PackMetaData(PACK_METADATA)
    original_created_date = obj.created

    obj.created = 'Obviously not a date'

    assert obj.created == original_created_date


def test_created_setter_datetime():
    obj = PackMetaData(PACK_METADATA)

    new_date_time = datetime(2020, 12, 31, 23, 59, 59)

    obj.created = new_date_time

    assert obj.created == new_date_time


def test_updated_setter_bad_string_data():
    obj = PackMetaData(PACK_METADATA)
    original_updated_date = obj.updated

    obj.updated = 'Obviously not a date'

    assert obj.updated == original_updated_date


def test_updated_setter_datetime():
    obj = PackMetaData(PACK_METADATA)

    new_date_time = datetime(2020, 12, 31, 23, 59, 59)

    obj.updated = new_date_time

    assert obj.updated == new_date_time


def test_legacy_setter():
    obj = PackMetaData(PACK_METADATA)

    obj.legacy = False
    assert not obj.legacy

    obj.legacy = True
    assert obj.legacy


@pytest.mark.parametrize('url, support, email, expected_url, expected_email', [
    ('some url', 'xsoar', 'some email', 'some url', 'some email'),
    (None, 'xsoar', 'some email', XSOAR_SUPPORT_URL, 'some email'),
    (None, 'Partner', None, None, None),
])
def test_support_details_getter(url, support, email, expected_url, expected_email):
    obj = PackMetaData(PACK_METADATA)
    obj.url = url
    obj.support = support
    obj.email = email

    support_details = obj.support_details

    assert expected_url == support_details.get('url')
    assert expected_email == support_details.get('email')


@pytest.mark.parametrize('support, author, expected_author, expected_log', [
    (XSOAR_SUPPORT, XSOAR_AUTHOR, XSOAR_AUTHOR, ''),
    ('someone', 'someone', 'someone', ''),
    (XSOAR_SUPPORT, 'someone', 'someone', f'someone author doest not match {XSOAR_AUTHOR} default value')
])
def test_author_getter(caplog, support, author, expected_author, expected_log):
    obj = PackMetaData(PACK_METADATA)
    obj.support = support
    obj.author = author

    assert obj.author == expected_author
    assert expected_log in caplog.text


@pytest.mark.parametrize('new_price, expected_price', [
    (10, 10),
    ('10', 10),
    ('not int', 0)
])
def test_price_setter_bad_int(new_price, expected_price):
    obj = PackMetaData(PACK_METADATA)

    obj.price = new_price

    assert obj.price == expected_price


def test_dump_with_price(mocker):
    def mock_json_dump(file_content, metadata_file, indent):
        assert file_content['premium'] is not None
        assert file_content['vendorId']
        assert file_content['vendorName']

    import json
    import builtins

    obj = PackMetaData(PACK_METADATA)
    obj.price = 1
    obj.premium = True
    obj.vendor_id = 'id'
    obj.vendor_name = 'name'

    mocker.patch.object(builtins, 'open', autospec=True)
    mocker.patch.object(json, 'dump', side_effect=mock_json_dump)

    obj.dump('metadata_file')
