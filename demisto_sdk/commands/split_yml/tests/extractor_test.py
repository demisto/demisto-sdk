from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import DEFAULT_IMAGE_BASE64
from demisto_sdk.commands.common.git_tools import git_path
import os
import base64


def test_extract_long_description():
    from demisto_sdk.commands.split_yml.extractor import Extractor

    # Test when script
    extractor = Extractor(input='script', output='', file_type='script', no_demisto_mock=False,
                          no_common_server=False, configuration=Configuration())
    assert extractor.extract_long_description('output_path') == 0

    # Test opening the file and writing to it
    extractor.input = f'{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml'
    extractor.file_type = 'integration'
    extractor.output = f'{git_path()}/demisto_sdk/tests/test_files/temp_text.txt'

    extractor.extract_long_description(extractor.output)
    with open(extractor.output, 'rb') as temp_description:
        assert temp_description.read().decode('utf-8') == 'detaileddescription'
    os.remove(extractor.output)


def test_extract_image():
    from demisto_sdk.commands.split_yml.extractor import Extractor

    # Test when script
    extractor = Extractor(input='script', output='', file_type='script', no_demisto_mock=False,
                          no_common_server=False, configuration=Configuration())
    assert extractor.extract_image('output_path') == 0

    # Test opening the file and writing to it
    extractor.input = f'{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml'
    extractor.file_type = 'integration'
    extractor.output = f'{git_path()}/demisto_sdk/tests/test_files/temp_image.png'

    extractor.extract_image(extractor.output)
    with open(extractor.output, 'rb') as temp_image:
        image_data = temp_image.read()
        image = base64.b64encode(image_data).decode('utf-8')
        assert image == DEFAULT_IMAGE_BASE64
    os.remove(extractor.output)


def test_extract_code():
    from demisto_sdk.commands.split_yml.extractor import Extractor
    extractor = Extractor(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml',
                          output=f'{git_path()}/demisto_sdk/tests/test_files/temp_code.txt', file_type='integration',
                          no_demisto_mock=False,
                          no_common_server=False, configuration=Configuration())

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
    os.remove(extractor.output)
