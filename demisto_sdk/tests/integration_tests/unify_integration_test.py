import json
import os

from click.testing import CliRunner

from demisto_sdk.__main__ import main
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    DASHBOARD, GENERIC_MODULE, UNIFIED_GENERIC_MODULE)
from TestSuite.test_tools import ChangeCWD

UNIFY_CMD = "unify"


class TestGenericModuleUnifier:
    def test_unify_generic_module(self, mocker, repo):
        """
        Given
        - A pack with a valid generic module, and a dashboard that it's id matches a dashboard in the generic module.

        When
        - Running unify on it.

        Then
        - Ensure the module was unified successfully (i.e contains the dashboard's content) and saved successfully
         in the output path.
        """
        pack = repo.create_pack('PackName')
        pack.create_generic_module("generic-module", GENERIC_MODULE)
        generic_module_path = pack.generic_modules[0].path
        dashboard_copy = DASHBOARD.copy()
        dashboard_copy['id'] = 'asset_dashboard'
        pack.create_dashboard('dashboard_1', dashboard_copy)
        saving_path = os.path.join(pack._generic_modules_path,
                                   f'{pack.generic_modules[0].name.rstrip(".json")}_unified.json')
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [UNIFY_CMD, '-i', generic_module_path], catch_exceptions=False)
        assert result.exit_code == 0
        assert os.path.isfile(saving_path)
        with open(saving_path) as f:
            saved_generic_module = json.load(f)
        assert saved_generic_module == UNIFIED_GENERIC_MODULE
