import pytest

from demisto_sdk.yaml_tools.update_integration import IntegrationYMLFormat

packs = [('/Users/teizenman/dev/demisto/demisto-sdk/tests/test_files/format_New_Integration_copy.yml',
          '/Users/teizenman/dev/demisto/demisto-sdk/tests/test_files/new_format_New_Integration_copy.yml')]


@pytest.mark.parametrize('source_path, destination_path', packs)
def test_remove_copy(source_path, destination_path):
    x = IntegrationYMLFormat(source_path, destination_path)
    x.format_file()
