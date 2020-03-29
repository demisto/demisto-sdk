from unittest.mock import patch

from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.upload.uploader import Uploader


@patch('demisto_client.configure')
def test_upload_sanity(mocked_configure=None):
    mocked_configure.return_value = "object"
    integration_pckg_path = f'{git_path()}demisto_sdk/tests/test_files/content_repo_example/Integrations/Securonix/'
    integration_pckg_uploader = Uploader(input=integration_pckg_path, insecure=False, verbose=False)
    with patch.object(integration_pckg_uploader, 'client', return_value='ok'):
        assert integration_pckg_uploader.upload() == 0


@patch('demisto_client.configure')
def test_upload_invalid_path(mocked_configure=None):
    mocked_configure.return_value = "object"

    script_dir_path = f'{git_path()}/demisto_sdk/tests/test_files/content_repo_example/Scripts/'
    script_dir_uploader = Uploader(input=script_dir_path, insecure=False, verbose=False)
    assert script_dir_uploader.upload() == 1
