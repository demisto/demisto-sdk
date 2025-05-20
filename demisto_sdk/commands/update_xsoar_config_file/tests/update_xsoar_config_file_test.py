from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree

import pytest
from typer.testing import CliRunner

from demisto_sdk.__main__ import app
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.commands.update_xsoar_config_file.update_xsoar_config_file import (
    XSOARConfigFileUpdater,
)

UNIT_TEST_DATA = src_root() / "commands" / "update_xsoar_config_file" / "tests" / "data"


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


class TestXSOARConfigFileUpdater:
    @pytest.mark.parametrize(
        argnames="add_all_marketplace_packs, expected_path, expected_outputs",
        argvalues=[
            (
                "--add-all-marketplace-packs",
                "xsoar_config.json",
                {"marketplace_packs": [{"id": "test1", "version": "1.0.0"}]},
            ),
        ],
    )
    def test_add_all_marketplace_packs(
        self, mocker, add_all_marketplace_packs, expected_path, expected_outputs
    ):
        """
        Given:
            - add_all_marketplace_packs arg as True or False
        When:
            - run the update_xsoar_config_file command
        Then:
            - validate the xsoar_config file exist in the destination output
            - validate the xsoar_config file output is as expected
        """

        mocker.patch.object(
            XSOARConfigFileUpdater,
            "get_installed_packs",
            return_value=[{"id": "test1", "version": "1.0.0"}],
        )
        runner = CliRunner()
        with temp_dir() as tmp_output_dir:
            file_path = (
                Path(tmp_output_dir) / expected_path
            )  # Get the expected file path

            # Run the command with the current flag value
            result = runner.invoke(
                app,
                args=[
                    "xsoar-config-file-update",
                    "--file-path",
                    str(file_path),
                    add_all_marketplace_packs,
                ],
            )
            assert result.exit_code == 0

            if add_all_marketplace_packs:
                assert file_path.exists()
                try:
                    with open(file_path, "r") as config_file:
                        config_file_info = json.load(config_file)
                except IsADirectoryError:
                    config_file_info = {}
                assert config_file_info == expected_outputs
            else:
                # When `add_all_marketplace_packs` is False, ensure the file does not exist
                assert not file_path.exists()

    def test_add_all_marketplace_packs_on_existing_list(self, mocker):
        """
        Given:
            - add_all_marketplace_packs arg as True
        When:
            - run the update_xsoar_config_file command
        Then:
            - validate the xsoar_config file exist in the destination output
            - validate the xsoar_config file output is as expected
        """

        mocker.patch.object(
            XSOARConfigFileUpdater,
            "get_installed_packs",
            return_value=[{"id": "test1", "version": "1.0.0"}],
        )

        with temp_dir() as tmp_output_dir:
            with open(f"{tmp_output_dir}/xsoar_config.json", "w") as config_file:
                json.dump(
                    {"marketplace_packs": [{"id": "test2", "version": "2.0.0"}]},
                    config_file,
                )
            runner = CliRunner()
            runner.invoke(
                app,
                args=[
                    "xsoar-config-file-update",
                    "--file-path",
                    tmp_output_dir / "xsoar_config.json",
                    "--add-all-marketplace-packs",
                ],
            )

            assert Path(f"{tmp_output_dir}/xsoar_config.json").exists()
            expected_path_object = Path(tmp_output_dir) / "xsoar_config.json"

            if expected_path_object.is_file():
                with open(expected_path_object) as config_file:
                    config_file_info = json.load(config_file)
            elif not expected_path_object.is_file():
                config_file_info = {}

            assert config_file_info == {
                "marketplace_packs": [
                    {"id": "test2", "version": "2.0.0"},
                    {"id": "test1", "version": "1.0.0"},
                ]
            }

    def test_add_marketplace_pack(self, capsys):
        """
        Given:
            - add_marketplace_pack arg as True
        When:
            - run the update_xsoar_config_file command
        Then:
            - validate the xsoar_config file exists in the destination output
            - validate the xsoar_config file output is as expected
        """

        with temp_dir() as tmp_output_dir:
            runner = CliRunner()

            # Prepare the file path for the config
            config_file_path = Path(tmp_output_dir) / "xsoar_config.json"
            result = runner.invoke(
                app,
                args=[
                    "xsoar-config-file-update",
                    "--file-path",
                    str(config_file_path),
                    "-mp",
                    "-pi",
                    "Pack1",
                    "-pd",
                    "1.0.1",
                ],
            )

            # Assert the result was successful (exit code 0)
            assert result.exit_code == 0

            # Check that the xsoar_config.json file was created
            assert config_file_path.exists()

            try:
                with open(config_file_path, "r") as config_file:
                    config_file_info = json.load(config_file)
            except IsADirectoryError:
                config_file_info = {}
            assert config_file_info == {
                "marketplace_packs": [{"id": "Pack1", "version": "1.0.1"}]
            }

    def test_add_custom_pack(self, capsys):
        """
        Given:
            - add_custom_pack arg as True
        When:
            - run the update_xsoar_config_file command
        Then:
            - validate the xsoar_config file exist in the destination output
            - validate the xsoar_config file output is as expected
        """

        with temp_dir() as tmp_output_dir:
            runner = CliRunner()
            config_file_path = Path(tmp_output_dir) / "xsoar_config.json"
            runner.invoke(
                app,
                args=[
                    "xsoar-config-file-update",
                    "--file-path",
                    str(config_file_path),
                    "-cp",
                    "-pi",
                    "Pack1",
                    "-pd",
                    "Packs/Pack1",
                ],
            )
            assert Path(f"{tmp_output_dir}/xsoar_config.json").exists()

            try:
                with open(config_file_path) as config_file:
                    config_file_info = json.load(config_file)
            except IsADirectoryError:
                config_file_info = {}
            assert config_file_info == {
                "custom_packs": [{"id": "Pack1", "url": "Packs/Pack1"}]
            }

    @pytest.mark.parametrize(
        argnames="add_marketplace_pack, pack_id, pack_data, expected_path, expected_outputs",
        argvalues=[
            (True, "", "1.0.1", "", {}),
            (True, "Pack1", "", "", {}),
        ],
    )
    def test_add_marketplace_pack_with_missing_args(
        self,
        add_marketplace_pack,
        pack_id,
        pack_data,
        expected_path,
        mocker,
        expected_outputs,
    ):
        """
        Given:
            - add_marketplace_pack arg as True without the mandatory args
        When:
            - run the update_xsoar_config_file command
        Then:
            - validate the xsoar_config file exist in the destination output
            - validate the xsoar_config file output is as expected
        """

        with temp_dir() as tmp_output_dir:
            runner = CliRunner()
            config_file_path = Path(tmp_output_dir) / "xsoar_config.json"
            runner.invoke(
                app,
                args=[
                    "xsoar-config-file-update",
                    "--file-path",
                    str(config_file_path),
                    "-mp",
                    "-pi",
                    pack_id,
                    "-pd",
                    pack_data,
                ],
            )
            assert Path(f"{tmp_output_dir}/{expected_path}").exists()

            try:
                with open(f"{tmp_output_dir}/{expected_path}") as config_file:
                    config_file_info = json.load(config_file)
            except IsADirectoryError:
                config_file_info = {}
            assert config_file_info == expected_outputs

    @pytest.mark.parametrize(
        argnames="add_custom_pack, pack_id, pack_data, expected_path, expected_outputs",
        argvalues=[
            (True, "", "Packs/Pack1", "", {}),
            (True, "Pack1", "", "", {}),
        ],
    )
    def test_add_custom_pack_with_missing_args(
        self,
        add_custom_pack,
        pack_id,
        pack_data,
        expected_path,
        expected_outputs,
    ):
        """
        Given:
            - add_custom_pack arg as True
        When:
            - run the update_xsoar_config_file command
        Then:
            - validate the xsoar_config file exist in the destination output
            - validate the xsoar_config file output is as expected
        """

        with temp_dir() as tmp_output_dir:
            runner = CliRunner()
            config_file_path = Path(tmp_output_dir) / "xsoar_config.json"
            runner.invoke(
                app,
                args=[
                    "xsoar-config-file-update",
                    "--file-path",
                    str(config_file_path),
                    "-cp",
                    "-pi",
                    pack_id,
                    "-pd",
                    pack_data,
                ],
            )
            assert Path(f"{tmp_output_dir}/{expected_path}").exists()

            try:
                with open(f"{tmp_output_dir}/{expected_path}") as config_file:
                    config_file_info = json.load(config_file)
            except IsADirectoryError:
                config_file_info = {}
            assert config_file_info == expected_outputs

    @pytest.mark.parametrize(
        argnames="add_custom_pack, pack_id, pack_data, err, exit_code",
        argvalues=[
            (
                True,
                "",
                "Packs/Pack1",
                "Error: Missing option '-pi' / '--pack-id'.",
                False,
            ),
            (True, "Pack1", "", "Error: Missing option '-pd' / '--pack-data'.", False),
            (True, "Pack1", "Packs/Pack1", "", True),
            (False, "Pack1", "", "", True),
        ],
    )
    def test_verify_flags(
        self,
        add_custom_pack,
        pack_id,
        pack_data,
        err,
        exit_code,
        caplog,
    ):
        """
        Given:
            - arguments to the xsoar-configuration-file
        When:
            - check that the flags is as expected
        Then:
            - validate the error code is as expected.
            - validate the Error message when the argument us missing
        """

        self.add_custom_pack = add_custom_pack
        self.pack_id = pack_id
        self.pack_data = pack_data
        config_file = XSOARConfigFileUpdater(
            pack_id, pack_data, add_custom_pack=add_custom_pack
        )
        error_code = config_file.verify_flags()
        assert error_code == exit_code

        if err:
            assert err in caplog.text

    @pytest.mark.parametrize(
        argnames="add_custom_pack, add_market_place_pack, pack_id, pack_data, exit_code",
        argvalues=[
            (True, False, "", "", 1),
            (False, True, "Pack1", "Packs/Pack1", 0),
            (False, False, "", "", 0),
        ],
    )
    def test_update_config_file_manager(
        self,
        mocker,
        add_custom_pack,
        add_market_place_pack,
        pack_id,
        pack_data,
        exit_code,
    ):
        """
        Given:
            - arguments to the xsoar-configuration-file
        When:
            - check that the update_config_file_manager works as expected
        Then:
            - validate the error code is as expected.
            - validate the Error message when the argument is missing
        """
        mocker.patch.object(XSOARConfigFileUpdater, "update_marketplace_pack")

        self.add_custom_pack = add_custom_pack
        self.pack_id = pack_id
        self.pack_data = pack_data
        self.add_marketplace_pack = add_market_place_pack
        config_file = XSOARConfigFileUpdater(
            pack_id,
            pack_data,
            add_marketplace_pack=add_market_place_pack,
            add_custom_pack=add_custom_pack,
        )
        error_code = config_file.update_config_file_manager()
        assert error_code == exit_code
