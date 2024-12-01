from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree, unpack_archive

import pytest
from typer.testing import CliRunner

from demisto_sdk.__main__ import app
from demisto_sdk.commands.common.tools import src_root
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
            ("--zip-all", "uploadable_packs.zip"),
            ("--no-zip-all", "uploadable_packs/TestPack.zip"),
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
        runner = CliRunner()
        with temp_dir() as tmp_output_dir:
            result = runner.invoke(
                app,
                args=[
                    "zip-packs",
                    "-i",
                    TEST_PACK_PATH,
                    "-o",
                    tmp_output_dir,
                    "--content-version",
                    "0.0.0",
                    zip_all,
                ],
            )
            assert result.exit_code == 0

            zip_file_path = Path(tmp_output_dir) / expected_path
            assert zip_file_path.exists(), f"{zip_file_path} does not exist"

    def test_zipped_packs(self):
        """
        Given:
            - zip_all arg as True
        When:
            - run the zip_packs command
        Then:
            - validate the zip file created and contain the pack zip inside it
        """

        runner = CliRunner()
        with temp_dir() as tmp_output_dir:
            runner.invoke(
                app,
                args=[
                    "zip-packs",
                    "-i",
                    TEST_PACK_PATH,
                    "-o",
                    tmp_output_dir,
                    "--content-version",
                    "0.0.0",
                    "--zip-all",
                ],
            )
            unpack_archive(f"{tmp_output_dir}/uploadable_packs.zip", tmp_output_dir)
            assert Path(f"{tmp_output_dir}/TestPack.zip").exists()

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
        runner = CliRunner()
        with temp_dir() as tmp_output_dir:
            runner.invoke(
                app,
                args=[
                    "zip-packs",
                    "-i",
                    "invalid_pack_name",
                    "-o",
                    tmp_output_dir,
                    "--content-version",
                    "0.0.0",
                    "--no-zip-all",
                ],
            )

            assert not Path(f"{tmp_output_dir}/uploadable_packs/TestPack.zip").exists()

    def test_not_exist_destination(self):
        """
        Given:
            - invalid destination
        When:
            - run the zip_packs command
        Then:
            - validate the missed directory is created and the zip is existed
        """
        with temp_dir() as tmp_output_dir:
            runner = CliRunner()
            runner.invoke(
                app,
                args=[
                    "zip-packs",
                    "-i",
                    TEST_PACK_PATH,
                    "-o",
                    tmp_output_dir,
                    "--content-version",
                    "0.0.0",
                    "--zip-all",
                ],
            )

            assert Path(f"{tmp_output_dir}/uploadable_packs.zip").exists()
