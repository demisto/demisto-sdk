import os
from contextlib import contextmanager
from datetime import datetime
from shutil import rmtree

import pytest
from packaging.version import parse

from demisto_sdk.commands.common.constants import (PACKS_DIR, XSOAR_AUTHOR,
                                                   XSOAR_SUPPORT,
                                                   XSOAR_SUPPORT_URL)
from demisto_sdk.commands.common.content.objects.pack_objects import \
    PackMetaData
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.logger import logging_setup
from demisto_sdk.commands.common.tools import src_root
from TestSuite.test_tools import ChangeCWD

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
PACK_METADATA = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / 'pack_metadata.json'
UNIT_TEST_DATA = (src_root() / 'commands' / 'create_artifacts' / 'tests' / 'data')


@contextmanager
def temp_dir():
    """Create Temp directory for test.

     Open:
        - Create temp directory.

    Close:
        - Delete temp directory.
    """
    temp = UNIT_TEST_DATA / 'temp'
    try:
        temp.mkdir(parents=True, exist_ok=True)
        yield temp
    finally:
        rmtree(temp)


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

    import builtins
    import json

    obj = PackMetaData(PACK_METADATA)
    obj.price = 1
    obj.premium = True
    obj.vendor_id = 'id'
    obj.vendor_name = 'name'

    mocker.patch.object(builtins, 'open', autospec=True)
    mocker.patch.object(json, 'dump', side_effect=mock_json_dump)

    obj.dump_metadata_file('metadata_file')


def test_load_user_metadata_basic(repo):
    """
    When:
        - Dumping a specific pack, processing the pack's metadata.

    Given:
        - Pack object.

    Then:
        - Verify that pack's metadata information was loaded successfully.

    """
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import \
        ArtifactsManager

    pack_1 = repo.setup_one_pack('Pack1')
    pack_1.pack_metadata.write_json(
        {
            'name': 'Pack Number 1',
            'description': 'A description for the pack',
            'created': '2020-06-08T15:37:54Z',
            'price': 0,
            'support': 'xsoar',
            'url': 'some url',
            'email': 'some email',
            'currentVersion': '1.1.1',
            'author': 'Cortex XSOAR',
            'tags': ['tag1'],
            'dependencies': [{'dependency': {'dependency': '1'}}]
        }
    )

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            artifact_manager = ArtifactsManager(artifacts_path=temp,
                                                content_version='6.0.0',
                                                zip=False,
                                                suffix='',
                                                cpus=1,
                                                packs=True)

    pack_1_metadata = artifact_manager.content.packs['Pack1'].metadata
    pack_1_metadata.load_user_metadata('Pack1', 'Pack Number 1', pack_1.path, logging_setup(3))

    assert pack_1_metadata.id == 'Pack1'
    assert pack_1_metadata.name == 'Pack Number 1'
    assert pack_1_metadata.description == 'A description for the pack'
    assert pack_1_metadata.created == datetime(2020, 6, 8, 15, 37, 54)
    assert pack_1_metadata.price == 0
    assert pack_1_metadata.support == 'xsoar'
    assert pack_1_metadata.url == 'some url'
    assert pack_1_metadata.email == 'some email'
    assert pack_1_metadata.certification == 'certified'
    assert pack_1_metadata.current_version == parse('1.1.1')
    assert pack_1_metadata.author == 'Cortex XSOAR'
    assert pack_1_metadata.tags == ['tag1']
    assert pack_1_metadata.dependencies == [{'dependency': {'dependency': '1'}}]


def test_load_user_metadata_advanced(repo):
    """
    When:
        - Dumping a specific pack, processing the pack's metadata.

    Given:
        - Pack object.

    Then:
        - Verify that pack's metadata information was loaded successfully.

    """
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import \
        ArtifactsManager

    pack_1 = repo.setup_one_pack('Pack1')
    pack_1.pack_metadata.write_json(
        {
            'name': 'Pack Number 1',
            'price': 10,
            'tags': ['tag1'],
            'useCases': ['usecase1'],
            'vendorId': 'vendorId',
            'vendorName': 'vendorName'
        }
    )

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            artifact_manager = ArtifactsManager(artifacts_path=temp,
                                                content_version='6.0.0',
                                                zip=False,
                                                suffix='',
                                                cpus=1,
                                                packs=True)

    pack_1_metadata = artifact_manager.content.packs['Pack1'].metadata
    pack_1_metadata.load_user_metadata('Pack1', 'Pack Number 1', pack_1.path, logging_setup(3))

    assert pack_1_metadata.id == 'Pack1'
    assert pack_1_metadata.name == 'Pack Number 1'
    assert pack_1_metadata.price == 10
    assert pack_1_metadata.vendor_id == 'vendorId'
    assert pack_1_metadata.vendor_name == 'vendorName'
    assert pack_1_metadata.tags == ['tag1', 'Use Case']


def test_load_user_metadata_no_metadata_file(repo, capsys):
    """
    When:
        - Dumping a pack with no pack_metadata file.

    Given:
        - Pack object.

    Then:
        - Verify that exceptions are written to the logger.

    """
    import demisto_sdk.commands.common.content.objects.pack_objects.pack_metadata.pack_metadata as metadata_class

    metadata_class.logger = logging_setup(3)

    pack_1 = repo.setup_one_pack('Pack1')
    pack_1.pack_metadata.write_json(
        {
            'name': 'Pack Number 1',
            'price': 'price',
            'tags': ['tag1'],
            'useCases': ['usecase1'],
            'vendorId': 'vendorId',
            'vendorName': 'vendorName'
        }
    )
    os.remove(pack_1.pack_metadata.path)

    content_object_pack = Pack(pack_1.path)
    pack_1_metadata = content_object_pack.metadata
    pack_1_metadata.load_user_metadata('Pack1', 'Pack Number 1', pack_1.path, logging_setup(3))

    captured = capsys.readouterr()
    assert 'Pack Number 1 pack is missing pack_metadata.json file.' in captured.out


def test_load_user_metadata_invalid_price(repo, capsys):
    """
    When:
        - Dumping a pack with invalid price in pack_metadata file.

    Given:
        - Pack object.

    Then:
        - Verify that exceptions are written to the logger.

    """
    import demisto_sdk.commands.common.content.objects.pack_objects.pack_metadata.pack_metadata as metadata_class

    metadata_class.logger = logging_setup(3)

    pack_1 = repo.setup_one_pack('Pack1')
    pack_1.pack_metadata.write_json(
        {
            'name': 'Pack Number 1',
            'price': 'price',
            'tags': ['tag1'],
            'useCases': ['usecase1'],
            'vendorId': 'vendorId',
            'vendorName': 'vendorName'
        }
    )

    content_object_pack = Pack(pack_1.path)
    pack_1_metadata = content_object_pack.metadata
    pack_1_metadata.load_user_metadata('Pack1', 'Pack Number 1', pack_1.path, logging_setup(3))
    captured = capsys.readouterr()

    assert 'Pack Number 1 pack price is not valid. The price was set to 0.' in captured.out


def test_load_user_metadata_bad_pack_metadata_file(repo, capsys):
    """
    When:
        - Dumping a pack with invalid pack_metadata file.

    Given:
        - Pack object.

    Then:
        - Verify that exceptions are written to the logger.

    """
    import demisto_sdk.commands.common.content.objects.pack_objects.pack_metadata.pack_metadata as metadata_class

    metadata_class.logger = logging_setup(3)

    pack_1 = repo.setup_one_pack('Pack1')
    pack_1.pack_metadata.write_as_text('Invalid of course {')
    content_object_pack = Pack(pack_1.path)

    pack_1_metadata = content_object_pack.metadata
    pack_1_metadata.load_user_metadata('Pack1', 'Pack Number 1', pack_1.path, logging_setup(3))

    captured = capsys.readouterr()
    assert 'Failed loading Pack Number 1 user metadata.' in captured.out
