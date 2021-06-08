from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree

import click
import pytest
from demisto_sdk.__main__ import compile_packs
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.commands.upload.uploader import Uploader

UNIT_TEST_DATA = (src_root() / 'commands' / 'compile_packs' / 'tests' / 'data')
TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_PACK_DIR = src_root() / 'Packs'
TEST_PACK_PATH = TEST_PACK_DIR / 'TestPack'


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


class TestPacksCompiler:
    """
    Happy path tests:
        1. Compile packs to one zip file (content_packs.zip)
        2. Compile zip to pack zip file (TestPack.zip)
        3. Compile packs with the Upload flag

    Edge cases tests:
        1. Invalid pack name
        2. Destination not exist

    """

    @pytest.mark.parametrize(argnames='zip_all, expected_path',
                             argvalues=[(True, 'content_packs.zip'),
                                        (False, 'uploadable_packs/TestPack.zip')])
    def test_compile_packs(self, zip_all, expected_path):
        """
        Given:
            - zip_all arg as True or False
        When:
            - run the compile_packs command
        Then:
            - validate the zip file exist in the destination output
        """

        with temp_dir() as tmp_output_dir:
            click.Context(command=compile_packs).invoke(compile_packs,
                                                        input=TEST_PACK_PATH.name,
                                                        output=tmp_output_dir,
                                                        content_version='0.0.0',
                                                        zip_all=zip_all)

            assert Path(f'{tmp_output_dir}/{expected_path}').exists()

    def test_compile_with_upload(self, mocker):
        """
        Given:
            - the upload flag is turn on
        When:
            - run the compile command
        Then:
            - validate the pack.zipped_pack_uploader was called with correct path
        """

        mocker.patch.object(Uploader, 'zipped_pack_uploader')

        with temp_dir() as tmp_output_dir:
            click.Context(command=compile_packs).invoke(compile_packs,
                                                        input=TEST_PACK_PATH.name,
                                                        output=tmp_output_dir,
                                                        content_version='0.0.0',
                                                        zip_all=True, upload=True)

            assert Uploader.zipped_pack_uploader.call_args.kwargs['path'] == f'{tmp_output_dir}/content_packs.zip'

    # Edge cases
    def test_invalid_pack_name(self):
        """
        Given:
            - invalid content pack name
        When:
            - run the compile pack command
        Then:
            - validate zip is not created
        """

        with temp_dir() as tmp_output_dir:
            click.Context(command=compile_packs).invoke(compile_packs,
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
            - run the compile pack command
        Then:
            - validate the missed directory is created and the zip is exist
        """
        with temp_dir() as tmp_output_dir:
            click.Context(command=compile_packs).invoke(compile_packs,
                                                        input=TEST_PACK_PATH.name,
                                                        output=tmp_output_dir,
                                                        content_version='0.0.0',
                                                        zip_all=True)

            assert Path(f'{tmp_output_dir}/content_packs.zip').exists()
