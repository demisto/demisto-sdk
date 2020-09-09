from os.path import join
from pathlib import Path
import git

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.lint.linter import Linter
from demisto_sdk.commands.lint.lint_manager import LintManager
from demisto_sdk.commands.common.constants import TYPE_PYTHON
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.hook_validations.image import ImageValidator
from demisto_sdk.commands.common.hook_validations.pack_unique_files import \
    PackUniqueFilesValidator
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.commands.find_dependencies.find_dependencies import \
    PackDependencies
from demisto_sdk.commands.validate.validate_manager import ValidateManager
from demisto_sdk.tests.constants_test import NOT_VALID_IMAGE_PATH
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    CONNECTION, DASHBOARD, INCIDENT_FIELD, INCIDENT_TYPE, INDICATOR_FIELD,
    LAYOUT, LAYOUTS_CONTAINER, MAPPER, NEW_CLASSIFIER, OLD_CLASSIFIER, REPORT,
    REPUTATION, WIDGET)
from TestSuite.test_tools import ChangeCWD
from git import Repo

LINT_CMD = "lint"


def test_xsoar_linter(mocker, repo):
    """
    Given
    - Valid `city` incident field.

    When
    - Running validation on it.

    Then
    - Ensure validation passes.
    - Ensure success validation message is printed.
    """

    pack = repo.create_pack('PackName')
    code = '''
    def main():
        sys.exit(0)
    print('test integration')
    sys.exit(0)
    '''
    pack.create_integration("integration", code=code)
    integration_path = pack.integrations[0].path
    facts = {
            "images": [],
            "python_version": 3.7,
            "env_vars": {},
            "test": False,
            "lint_files": [integration_path],
            "support_level": 'base',
            "lint_unittest_files": [],
            "additional_requirements": [],
            "docker_engine": None
        }
    pkg_lint_status = {
        "pkg": None,
        "pack_type": TYPE_PYTHON,
        "path": str(repo.path),
        "errors": [],
        "images": [],
        "flake8_errors": None,
        "xsoar_linter_errors": None,
        "bandit_errors": None,
        "mypy_errors": None,
        "vulture_errors": None,
        "exit_code": 0b0
    }
    manager_facts = {
            "content_repo": repo,
            "requirements_3": None,
            "requirements_2": None,
            "test_modules": None,
            "docker_engine": False
        }
    mocker.patch.object(LintManager, '_gather_facts', return_value=manager_facts)
    mocker.patch.object(LintManager, '_get_packages', return_value=[integration_path])
    mocker.patch.object(Repo, 'working_dir', return_value=repo.path)

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [LINT_CMD, '-i', integration_path], catch_exceptions=False)
    assert result.exit_code == 0
