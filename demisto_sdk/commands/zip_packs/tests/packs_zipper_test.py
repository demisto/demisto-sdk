from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree, unpack_archive

import click
import demisto_client
import pytest
from demisto_client.demisto_api import DefaultApi
from packaging.version import parse

from demisto_sdk.__main__ import zip_packs
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.commands.upload import uploader
from demisto_sdk.commands.upload.uploader import Uploader
from demisto_sdk.tests.constants_test import PACK_TARGET

UNIT_TEST_DATA = src_root() / "commands" / "zip_packs" / "tests" / "data"
TEST_PACK_PATH = Path(PACK_TARGET)


@contextmanager
def temp_dir():
    """Create Temp directory for test.

     Open:
        - Create temp directory.

    Close:
        - Delete temp directory.
    """
    temp = UNIT_TEST_DATA / "temp"
    try:
        temp.mkdir(parents=True, exist_ok=True)
        yield temp
    finally:
        rmtree(temp)


class TestPacksZipper:
    """
    Happy path tests:
        1. Zip packs to one zip file (content_packs.zip)
        2. Zip pack to pack zip file (TestPack.zip)
        3. Zip packs with the Upload flag
        4. Zip packs to zip files to ensure the created file are zip of zips

    Edge cases tests:
        1. Invalid pack name
        2. Destination not exist

    """

    @pytest.mark.parametrize(
        argnames="zip_all, expected_path",
        argvalues=[
            (True, "uploadable_packs.zip"),
            (False, "uploadable_packs/TestPack.zip"),
        ],
    )
    def test_zip_packs(self, zip_all, expected_path):
        """
        Given:
            - zip_all arg as True or False
        When:
            - run the zip_packs command
        Then:
            - validate the zip file exist in the destination output
        """

        with temp_dir() as tmp_output_dir:
            click.Context(command=zip_packs).invoke(
                zip_packs,
                input=TEST_PACK_PATH,
                output=tmp_output_dir,
                content_version="0.0.0",
                zip_all=zip_all,
            )

            assert Path(f"{tmp_output_dir}/{expected_path}").exists()

    def test_zipped_packs(self):
        """
        Given:
            - zip_all arg as True
        When:
            - run the zip_packs command
        Then:
            - validate the zip file created and contain the pack zip inside it
        """

        with temp_dir() as tmp_output_dir:
            click.Context(command=zip_packs).invoke(
                zip_packs,
                input=TEST_PACK_PATH,
                output=tmp_output_dir,
                content_version="0.0.0",
                zip_all=True,
            )
            unpack_archive(f"{tmp_output_dir}/uploadable_packs.zip", tmp_output_dir)
            assert Path(f"{tmp_output_dir}/TestPack.zip").exists()

    def test_zip_with_upload(self, mocker):
        """
        Given:
            - the upload flag is turn on
        When:
            - run the zip_packs command
        Then:
            - validate the upload command was called once
        """
        mocker.patch.object(demisto_client, "configure", return_value=DefaultApi())
        mocker.patch.object(
            uploader, "get_demisto_version", return_value=parse("6.0.0")
        )
        mocker.patch.object(Uploader, "upload")

        with temp_dir() as tmp_output_dir:
            click.Context(command=zip_packs).invoke(
                zip_packs,
                input=TEST_PACK_PATH,
                output=tmp_output_dir,
                content_version="0.0.0",
                zip_all=True,
                upload=True,
            )

            assert Uploader.upload.called_once()

    # Edge cases
    def test_invalid_pack_name(self):
        """
        Given:
            - invalid content pack name
        When:
            - run the zip_packs command
        Then:
            - validate zip is not created
        """

        with temp_dir() as tmp_output_dir:
            click.Context(command=zip_packs).invoke(
                zip_packs,
                input="invalid_pack_name",
                output=tmp_output_dir,
                content_version="0.0.0",
                zip_all=False,
            )

            assert not Path(f"{tmp_output_dir}/uploadable_packs/TestPack.zip").exists()

    def test_not_exist_destination(self):
        """
        Given:
            - invalid destination
        When:
            - run the zip_packs command
        Then:
            - validate the missed directory is created and the zip is exist
        """
        with temp_dir() as tmp_output_dir:
            click.Context(command=zip_packs).invoke(
                zip_packs,
                input=TEST_PACK_PATH,
                output=tmp_output_dir,
                content_version="0.0.0",
                zip_all=True,
            )

            assert Path(f"{tmp_output_dir}/uploadable_packs.zip").exists()
