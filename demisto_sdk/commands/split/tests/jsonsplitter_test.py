import json
import os

from demisto_sdk.commands.split.jsonsplitter import JsonSplitter
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    GENERIC_MODULE, UNIFIED_GENERIC_MODULE)
from TestSuite.test_tools import ChangeCWD

EXTRACTED_DASHBOARD = UNIFIED_GENERIC_MODULE.get('views')[0].get('tabs')[0].get('dashboard')


def test_split_json(repo):
    """
    Given
        - Valid a unified generic module.

    When
        - Running split on it.

    Then
        - Ensure dashboard is extracted to the requested location.
        - Ensure the generic module file is edited properly in place.
    """
    pack = repo.create_pack('PackName')
    pack.create_generic_module("generic-module", UNIFIED_GENERIC_MODULE)
    generic_module_path = pack.generic_modules[0].path
    json_splitter = JsonSplitter(input=generic_module_path, output=pack.path)
    expected_dashboard_path = str(pack.path) + "/" + EXTRACTED_DASHBOARD.get('name') + '.json'

    with ChangeCWD(pack.repo_path):
        res = json_splitter.split_json()
        assert res == 0
        assert os.path.isfile(expected_dashboard_path)

        with open(expected_dashboard_path, 'r') as f:
            result_dashboard = json.load(f)

        assert result_dashboard == EXTRACTED_DASHBOARD

        with open(generic_module_path, 'r') as f:
            result_generic_module = json.load(f)

        assert result_generic_module == GENERIC_MODULE
