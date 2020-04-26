import pytest
import demisto_client
from unittest.mock import patch

from demisto_sdk.commands.common.constants import BETA_INTEGRATIONS_DIR, INTEGRATIONS_DIR, SCRIPTS_DIR, CLASSIFIERS_DIR, \
    LAYOUTS_DIR, TEST_PLAYBOOKS_DIR
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.upload.uploader import Uploader


@pytest.fixture
def demisto_client_configure(mocker):
    mocker.patch.object(demisto_client, 'configure', return_value="object")


def test_upload_sanity(demisto_client_configure):
    integration_pckg_path = f'{git_path()}demisto_sdk/tests/test_files/content_repo_example/Integrations/Securonix/'
    integration_pckg_uploader = Uploader(input=integration_pckg_path, insecure=False, verbose=False)
    with patch.object(integration_pckg_uploader, 'client', return_value='ok'):
        assert integration_pckg_uploader.upload() == 0


def test_upload_invalid_path(demisto_client_configure):
    script_dir_path = f'{git_path()}/demisto_sdk/tests/test_files/content_repo_example/Scripts/'
    script_dir_uploader = Uploader(input=script_dir_path, insecure=False, verbose=False)
    assert script_dir_uploader.upload() == 1


def test_sort_directories_based_on_dependencies(demisto_client_configure):
    """
    Given
        - An empty (no given input path) Uploader object
        - List of non-sorted (based on dependencies) content directories

    When
        - Running sort_directories_based_on_dependencies on the list

    Then
        - Ensure a sorted listed of the directories is returned
    """
    dir_list = [TEST_PLAYBOOKS_DIR, BETA_INTEGRATIONS_DIR, INTEGRATIONS_DIR, SCRIPTS_DIR, CLASSIFIERS_DIR, LAYOUTS_DIR]
    uploader = Uploader(input="", insecure=False, verbose=False)
    sorted_dir_list = uploader._sort_directories_based_on_dependencies(dir_list)
    assert sorted_dir_list == [INTEGRATIONS_DIR, BETA_INTEGRATIONS_DIR, SCRIPTS_DIR, TEST_PLAYBOOKS_DIR,
                               CLASSIFIERS_DIR, LAYOUTS_DIR]
