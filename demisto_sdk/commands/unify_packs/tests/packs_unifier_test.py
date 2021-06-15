from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree, unpack_archive

import click
import demisto_client
import pytest
from demisto_client.demisto_api import DefaultApi
from demisto_sdk.__main__ import unify_packs
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.commands.upload import uploader
from demisto_sdk.commands.upload.uploader import Uploader
from packaging.version import parse

UNIT_TEST_DATA = (src_root() / 'commands' / 'unify_packs' / 'tests' / 'data')
TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_PACK_DIR = src_root() / 'Packs'
TEST_PACK_PATH = src_root().parent / 'Packs' / 'TestPack'


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


class TestPacksUnifier:
    """
    Happy path tests:
        1. Unify packs to one zip file (content_packs.zip)
        2. Unify pack to pack zip file (TestPack.zip)
        3. Unify packs with the Upload flag
        4. Unify packs to zip files to ensure the created file are zip of zips

    Edge cases tests:
        1. Invalid pack name
        2. Destination not exist

    """

    @pytest.mark.parametrize(argnames='zip_all, expected_path',
                             argvalues=[(True, 'uploadable_packs.zip'),
                                        (False, 'uploadable_packs/TestPack.zip')])
    def test_unify_packs(self, zip_all, expected_path):
        """
        Given:
            - zip_all arg as True or False
        When:
            - run the unify_packs command
        Then:
            - validate the zip file exist in the destination output
        """

        with temp_dir() as tmp_output_dir:
            click.Context(command=unify_packs).invoke(unify_packs,
                                                      input=TEST_PACK_PATH,
                                                      output=tmp_output_dir,
                                                      content_version='0.0.0',
                                                      zip_all=zip_all)

            assert Path(f'{tmp_output_dir}/{expected_path}').exists()

    def test_zipped_packs(self):
        """
        Given:
            - zip_all arg as True
        When:
            - run the unify_packs command
        Then:
            - validate the zip file created and contain the pack zip inside it
        """

        with temp_dir() as tmp_output_dir:
            click.Context(command=unify_packs).invoke(unify_packs,
                                                      input=TEST_PACK_PATH,
                                                      output=tmp_output_dir,
                                                      content_version='0.0.0',
                                                      zip_all=True)
            unpack_archive(f'{tmp_output_dir}/uploadable_packs.zip', tmp_output_dir)
            assert Path(f'{tmp_output_dir}/TestPack.zip').exists()

    def test_unify_with_upload(self, mocker):
        """
        Given:
            - the upload flag is turn on
        When:
            - run the unify_packs command
        Then:
            - validate the pack.zipped_pack_uploader was called with correct path
        """
        mocker.patch.object(demisto_client, 'configure', return_value=DefaultApi())
        mocker.patch.object(uploader, 'get_demisto_version', return_value=parse('6.0.0'))
        mocker.patch.object(Uploader, 'zipped_pack_uploader')

        with temp_dir() as tmp_output_dir:
            click.Context(command=unify_packs).invoke(unify_packs,
                                                      input=TEST_PACK_PATH,
                                                      output=tmp_output_dir,
                                                      content_version='0.0.0',
                                                      zip_all=True, upload=True)

            assert Uploader.zipped_pack_uploader.call_args.kwargs['path'] == f'{tmp_output_dir}/uploadable_packs.zip'

    # Edge cases
    def test_invalid_pack_name(self):
        """
        Given:
            - invalid content pack name
        When:
            - run the unify_packs command
        Then:
            - validate zip is not created
        """

        with temp_dir() as tmp_output_dir:
            click.Context(command=unify_packs).invoke(unify_packs,
                                                      input='invalid_pack_name',
                                                      output=tmp_output_dir,
                                                      content_version='0.0.0',
                                                      zip_all=False)

            assert not Path(f'{tmp_output_dir}/uploadable_packs/TestPack.zip').exists()

    def test_not_exist_destination(self):
        """
        Given:
            - invalid destination
        When:
            - run the unify_packs command
        Then:
            - validate the missed directory is created and the zip is exist
        """
        with temp_dir() as tmp_output_dir:
            click.Context(command=unify_packs).invoke(unify_packs,
                                                      input=TEST_PACK_PATH,
                                                      output=tmp_output_dir,
                                                      content_version='0.0.0',
                                                      zip_all=True)

            assert Path(f'{tmp_output_dir}/uploadable_packs.zip').exists()
