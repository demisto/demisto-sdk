from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import DEFAULT_IMAGE_BASE64
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.split_yml.extractor import Extractor
import os
import base64


def test_extract_long_description(tmpdir):

    # Test when script
    extractor = Extractor(input=f'{git_path()}/demisto_sdk/tests/test_files/script-test_script.yml',
                          output='', file_type='script', no_demisto_mock=False,
                          no_common_server=False, configuration=Configuration())
    assert extractor.extract_long_description('output_path') == 0

    # Test opening the file and writing to it
    extractor = Extractor(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml',
                          output=str(tmpdir.join('temp_text.txt')), file_type='integration')

    extractor.extract_long_description(extractor.output)
    with open(extractor.output, 'rb') as temp_description:
        assert temp_description.read().decode('utf-8') == 'detaileddescription'
    os.remove(extractor.output)


def test_extract_image(tmpdir):

    # Test when script
    extractor = Extractor(input=f'{git_path()}/demisto_sdk/tests/test_files/script-test_script.yml',
                          output='', file_type='script')
    assert extractor.extract_image('output_path') == 0

    # Test opening the file and writing to it
    extractor = Extractor(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml',
                          output=str(tmpdir.join('temp_image.png')), file_type='integration')

    extractor.extract_image(extractor.output)
    with open(extractor.output, 'rb') as temp_image:
        image_data = temp_image.read()
        image = base64.b64encode(image_data).decode('utf-8')
        assert image == DEFAULT_IMAGE_BASE64


def test_extract_code(tmpdir):
    extractor = Extractor(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml',
                          output=str(tmpdir.join('temp_code.py')), file_type='integration')

    extractor.extract_code(extractor.output)
    with open(extractor.output, 'rb') as temp_code:
        file_data = temp_code.read().decode('utf-8')
        assert 'import demistomock as demisto\n' in file_data
        assert 'from CommonServerPython import *\n' in file_data
        assert file_data[-1] == '\n'
    os.remove(extractor.output)

    extractor.common_server = False
    extractor.demisto_mock = False
    extractor.extract_code(extractor.output)
    with open(extractor.output, 'rb') as temp_code:
        file_data = temp_code.read().decode('utf-8')
        assert 'import demistomock as demisto\n' not in file_data
        assert 'from CommonServerPython import *\n' not in file_data
        assert file_data[-1] == '\n'


def test_extract_code_pwsh(tmpdir):
    extractor = Extractor(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-powershell_ssh_remote.yml',
                          output=str(tmpdir.join('temp_code')), file_type='integration')

    extractor.extract_code(extractor.output)
    # notice that we passed without an extension. Extractor should be adding .ps1
    with open(extractor.output + '.ps1', 'r', encoding='utf-8') as temp_code:
        file_data = temp_code.read()
        assert '. $PSScriptRoot\\CommonServerPowerShell.ps1\n' in file_data
        assert file_data[-1] == '\n'


def test_get_output_path():
    out = f'{git_path()}/demisto_sdk/tests/Integrations'
    extractor = Extractor(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml',
                          file_type='integration',
                          output=out)
    res = extractor.get_output_path()
    assert res == out + "/Zoom"
