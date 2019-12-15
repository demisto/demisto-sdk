import pytest

from demisto_sdk.yaml_tools.update_integration import IntegrationYMLFormat


@pytest.mark.parametrize('path', ['/Users/teizenman/dev/demisto/demisto-sdk/tests/test_files/format_New_Integration_copy.yml'])
def test_remove_copy(path):
    x = IntegrationYMLFormat(path)
    x.format_file()
