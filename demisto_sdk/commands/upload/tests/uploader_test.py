from unittest.mock import patch

from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.upload.uploader import Uploader


@patch('demisto_client.configure')
def test_upload(mocked_configure=None):
    mocked_configure.return_value = ""

    test_playbook_path = f'{git_path()}/demisto_sdk/tests/test_files/content_repo_example/TestPlaybooks'
    test_playbook_uploader = Uploader(input=test_playbook_path, insecure=False, verbose=False)
    assert test_playbook_uploader.upload() == 1

    script_yml_path = f'{git_path()}demisto_sdk/tests/test_files/content_repo_example/Scripts/script-Sleep.yml'
    script_yml_path_uploader = Uploader(input=script_yml_path, insecure=False, verbose=False)
    assert script_yml_path_uploader.upload() == 1
