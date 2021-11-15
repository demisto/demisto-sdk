import json
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree

import click
import pytest

from demisto_sdk.__main__ import xsoar_config_file_update
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.commands.xsoar_config_file.xsoar_config_file import \
    XSOARConfigFileUpdater

UNIT_TEST_DATA = (src_root() / 'commands' / 'xsoar_config_file' / 'tests' / 'data')


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


class TestXSOARConfigFileUpdater:
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

    @pytest.mark.parametrize(argnames='add_all_marketplace_packs, expected_path, expected_outputs',
                             argvalues=[(True, 'xsoar_config.json',
                                         {'marketplace_packs': [{'id': 'test1', 'version': '1.0.0'}]}),
                                        (False, '', {})])
    def test_add_all_marketplace_packs(self, mocker, add_all_marketplace_packs, expected_path, expected_outputs):
        """
        Given:
            - add_all_marketplace_packs arg as True or False
        When:
            - run the xsoar_config_file command
        Then:
            - validate the xsoar_config file exist in the destination output
            - validate the xsoar_config file output is as expected
        """

        mocker.patch.object(XSOARConfigFileUpdater, 'get_installed_packs', return_value=[
            {"id": "test1", "version": "1.0.0"}])
        with temp_dir() as tmp_output_dir:
            click.Context(command=xsoar_config_file_update).invoke(
                xsoar_config_file_update,
                file_path=tmp_output_dir / 'xsoar_config.json',
                add_all_marketplace_packs=add_all_marketplace_packs
            )

            assert Path(f'{tmp_output_dir}/{expected_path}').exists()

            try:
                with open(f'{tmp_output_dir}/{expected_path}', 'r') as config_file:
                    config_file_info = json.load(config_file)
            except IsADirectoryError:
                config_file_info = {}
            assert config_file_info == expected_outputs

    @pytest.mark.parametrize(argnames='add_marketplace_pack, pack_id, pack_data, expected_path, err, expected_outputs',
                             argvalues=[(True, 'Pack1', '1.0.1', 'xsoar_config.json', '',
                                         {'marketplace_packs': [{'id': 'Pack1', 'version': '1.0.1'}]}),
                                        (True, '', '1.0.1', '', "Error: Missing option '-pi' / '--pack-id'.", {}),
                                        (True, 'Pack1', '', '', "Error: Missing option '-pd' / '--pack-data'.", {})])
    def test_add_marketplace_pack(self, add_marketplace_pack, pack_id, pack_data, expected_path, capsys, err,
                                  expected_outputs):
        """
        Given:
            - add_marketplace_pack arg as True
        When:
            - run the xsoar_config_file command
        Then:
            - validate the xsoar_config file exist in the destination output
            - validate the Error massage when the argument us missing
            - validate the xsoar_config file output is as expected
        """

        with temp_dir() as tmp_output_dir:
            click.Context(command=xsoar_config_file_update).invoke(xsoar_config_file_update,
                                                                   file_path=tmp_output_dir / 'xsoar_config.json',
                                                                   add_marketplace_pack=add_marketplace_pack,
                                                                   pack_id=pack_id,
                                                                   pack_data=pack_data)
            assert Path(f'{tmp_output_dir}/{expected_path}').exists()

            stdout, _ = capsys.readouterr()
            if err:
                assert err in stdout

            try:
                with open(f'{tmp_output_dir}/{expected_path}', 'r') as config_file:
                    config_file_info = json.load(config_file)
            except IsADirectoryError:
                config_file_info = {}
            assert config_file_info == expected_outputs

    @pytest.mark.parametrize(argnames='add_custom_pack, pack_id, pack_data, expected_path, err, expected_outputs',
                             argvalues=[(True, 'Pack1', 'Packs/Pack1', 'xsoar_config.json', '',
                                         {'custom_packs': [{'id': 'Pack1', 'url': 'Packs/Pack1'}]}),
                                        (True, '', 'Packs/Pack1', '', "Error: Missing option '-pi' / '--pack-id'.", {}),
                                        (True, 'Pack1', '', '', "Error: Missing option '-pd' / '--pack-data'.", {})])
    def test_add_custom_pack(self, add_custom_pack, pack_id, pack_data, expected_path, capsys, err,
                             expected_outputs):
        """
        Given:
            - add_custom_pack arg as True
        When:
            - run the xsoar_config_file command
        Then:
            - validate the xsoar_config file exist in the destination output
            - validate the Error massage when the argument us missing
            - validate the xsoar_config file output is as expected
        """

        with temp_dir() as tmp_output_dir:
            click.Context(command=xsoar_config_file_update).invoke(xsoar_config_file_update,
                                                                   file_path=tmp_output_dir / 'xsoar_config.json',
                                                                   add_custom_pack=add_custom_pack,
                                                                   pack_id=pack_id,
                                                                   pack_data=pack_data)
            assert Path(f'{tmp_output_dir}/{expected_path}').exists()

            stdout, _ = capsys.readouterr()
            if err:
                assert err in stdout

            try:
                with open(f'{tmp_output_dir}/{expected_path}', 'r') as config_file:
                    config_file_info = json.load(config_file)
            except IsADirectoryError:
                config_file_info = {}
            assert config_file_info == expected_outputs
