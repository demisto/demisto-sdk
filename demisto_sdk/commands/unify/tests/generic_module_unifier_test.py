import json
import os

import pytest

from demisto_sdk.commands.unify.generic_module_unifier import \
    GenericModuleUnifier
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    DASHBOARD, GENERIC_MODULE, UNIFIED_GENERIC_MODULE)
from TestSuite.test_tools import ChangeCWD


def test_find_dashboard_by_id_positive(repo):
    """
    Given
    - A dashboard id to test
    - A pack with a valid generic module, and two dashboards which one of them contains the tested id.

    When
    - Running GenericModuleUnifier.find_dashboard_by_id

    Then
    - Ensure the found dashboard equals to the dashboard in the given pack that contains the tested id.
    """
    id_to_test = 'test'
    pack = repo.create_pack('PackName')
    pack.create_generic_module("generic-module", GENERIC_MODULE)
    generic_module_path = pack.generic_modules[0].path
    pack.create_dashboard('dashboard_1', DASHBOARD)
    dashboard_copy = DASHBOARD.copy()
    dashboard_copy['id'] = id_to_test
    pack.create_dashboard('dashboard_2', dashboard_copy)
    with ChangeCWD(pack.repo_path):
        unifier = GenericModuleUnifier(input=generic_module_path)
        found_dashboard = unifier.find_dashboard_by_id(dashboard_id=id_to_test)
        assert found_dashboard == dashboard_copy


def test_find_dashboard_by_id_negative(repo):
    """
    Given
    - A dashboard id to test
    - A pack with a valid generic module, and two dashboards that none of them contains the tested id.

    When
    - Running GenericModuleUnifier.find_dashboard_by_id

    Then
    - Ensure no dashboard was found.
    """
    id_to_test = 'test'
    pack = repo.create_pack('PackName')
    pack.create_generic_module("generic-module", GENERIC_MODULE)
    generic_module_path = pack.generic_modules[0].path
    pack.create_dashboard('dashboard_1', DASHBOARD)
    dashboard_copy = DASHBOARD.copy()
    dashboard_copy['id'] = 'wrong_id'
    pack.create_dashboard('dashboard_2', dashboard_copy)
    with ChangeCWD(pack.repo_path):
        unifier = GenericModuleUnifier(input=generic_module_path)
        found_dashboard = unifier.find_dashboard_by_id(dashboard_id=id_to_test)
        assert found_dashboard is None


def test_merge_generic_module_with_its_dashboards_positive(repo):
    """
    Given
    - A pack with a valid generic module, and a dashboard that it's id matches a dashboard in the generic module.

    When
    - Running GenericModuleUnifier.merge_generic_module_with_its_dashboards()

    Then
    - Ensure the module was unified successfully - i.e contains the dashboard's content
    """
    pack = repo.create_pack('PackName')
    pack.create_generic_module("generic-module", GENERIC_MODULE)
    generic_module_path = pack.generic_modules[0].path
    dashboard_copy = DASHBOARD.copy()
    dashboard_copy['id'] = 'asset_dashboard'
    pack.create_dashboard('dashboard_1', dashboard_copy)
    with ChangeCWD(pack.repo_path):
        unifier = GenericModuleUnifier(input=generic_module_path)
        unified_generic_module = unifier.merge_generic_module_with_its_dashboards()
        assert unified_generic_module == UNIFIED_GENERIC_MODULE


def test_merge_generic_module_with_its_dashboards_negative(repo, capsys):
    """
    Given
    - A pack with a valid generic module, and no dashboard that it's id matches a dashboard in the generic module.

    When
    - Running GenericModuleUnifier.merge_generic_module_with_its_dashboards()

    Then
    - Ensure the module wasn't unified.
    - Ensure a suitable error message was printed.
    """
    pack = repo.create_pack('PackName')
    pack.create_generic_module("generic-module", GENERIC_MODULE)
    generic_module_path = pack.generic_modules[0].path
    generic_module_dash_id = GENERIC_MODULE.get('views', {})[0].get('tabs', {})[0].get('dashboard', {}).get('id')
    pack.create_dashboard('dashboard_1', DASHBOARD)
    with ChangeCWD(pack.repo_path):
        unifier = GenericModuleUnifier(input=generic_module_path)
        non_unified_generic_module = unifier.merge_generic_module_with_its_dashboards()
        assert non_unified_generic_module == GENERIC_MODULE
        err_msg = capsys.readouterr()
        assert f'Dashboard {generic_module_dash_id} was not found in pack: PackName and therefore was not unified\n' in\
               err_msg


def test_save_unified_generic_module(repo):
    """
    Given
    - A unified generic module, and a desirable saving path.

    When
    - Running GenericModuleUnifier.save_unified_generic_module()

    Then
    - Ensure the module was saved successfully in the desirable path.
    """
    pack = repo.create_pack('PackName')
    pack.create_generic_module("generic-module", GENERIC_MODULE)
    generic_module_path = pack.generic_modules[0].path
    with ChangeCWD(pack.repo_path):
        unifier = GenericModuleUnifier(input=generic_module_path, output=pack._dashboards_path)
        unifier.save_unified_generic_module(unified_generic_module_json=UNIFIED_GENERIC_MODULE)
        saving_path = os.path.join(pack._dashboards_path, f'{pack.generic_modules[0].name.rstrip(".json")}_unified.json')
        assert os.path.isfile(saving_path)
        with open(saving_path) as f:
            saved_generic_module = json.load(f)
        assert saved_generic_module == UNIFIED_GENERIC_MODULE


def test_save_unified_generic_module_without_saving_path(repo):
    """
    Given
    - A unified generic module

    When
    - Running GenericModuleUnifier.save_unified_generic_module()

    Then
    - Ensure the module was saved successfully in the unifier's input path.
    """
    pack = repo.create_pack('PackName')
    pack.create_generic_module("generic-module", GENERIC_MODULE)
    generic_module_path = pack.generic_modules[0].path
    with ChangeCWD(pack.repo_path):
        unifier = GenericModuleUnifier(input=generic_module_path)
        unifier.save_unified_generic_module(unified_generic_module_json=UNIFIED_GENERIC_MODULE)
        saving_path = os.path.join(pack._generic_modules_path,
                                   f'{pack.generic_modules[0].name.rstrip(".json")}_unified.json')
        assert os.path.isfile(saving_path)
        with open(saving_path) as f:
            saved_generic_module = json.load(f)
        assert saved_generic_module == UNIFIED_GENERIC_MODULE


def test_save_unified_generic_module_file_is_already_exist(repo, capsys):
    """
    Given
    - A unified generic module, and a desirable saving path.
    - a unified GenericModule file with the same name is already exist in the given saving path.

    When
    - Running GenericModuleUnifier.save_unified_generic_module()

    Then
    - Ensure the module was saved successfully in the desirable path.
    - Ensure a suitable exception was raised.
    """
    pack = repo.create_pack('PackName')
    pack.create_generic_module("generic-module", GENERIC_MODULE)
    generic_module_path = pack.generic_modules[0].path
    with ChangeCWD(pack.repo_path):
        unifier = GenericModuleUnifier(input=generic_module_path, output=pack._dashboards_path)
        unifier.save_unified_generic_module(unified_generic_module_json=UNIFIED_GENERIC_MODULE)
        # try to save a different GenericModule in the same path - An exception should be raised:
        with pytest.raises(ValueError, match='Output file already exists'):
            unifier.save_unified_generic_module(unified_generic_module_json=GENERIC_MODULE)
        saving_path = os.path.join(pack._dashboards_path, f'{pack.generic_modules[0].name.rstrip(".json")}_unified.json')
        with open(saving_path) as f:
            saved_generic_module = json.load(f)
        assert saved_generic_module == UNIFIED_GENERIC_MODULE


def test_save_unified_generic_module_file_is_already_exist_force(repo, capsys):
    """
    Given
    - A unified generic module, and a desirable saving path.
    - a unified GenericModule file with the same name is already exist in the given saving path.

    When
    - Running GenericModuleUnifier.save_unified_generic_module() with force = True

    Then
    - Ensure the module was saved in the desirable path.
    """
    pack = repo.create_pack('PackName')
    pack.create_generic_module("generic-module", GENERIC_MODULE)
    generic_module_path = pack.generic_modules[0].path
    with ChangeCWD(pack.repo_path):
        unifier = GenericModuleUnifier(input=generic_module_path, output=pack._dashboards_path, force=True)
        unifier.save_unified_generic_module(unified_generic_module_json=UNIFIED_GENERIC_MODULE)
        # try to save a different GenericModule in the same path - should succeed because force arg is true:
        unifier.save_unified_generic_module(unified_generic_module_json=GENERIC_MODULE)
        saving_path = os.path.join(pack._dashboards_path, f'{pack.generic_modules[0].name.rstrip(".json")}_unified.json')
        with open(saving_path) as f:
            saved_generic_module = json.load(f)
        assert saved_generic_module == GENERIC_MODULE
