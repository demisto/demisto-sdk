from pytest import raises
from mock import patch
from demisto_sdk.common.configuration import Configuration
from demisto_sdk.common.constants import DEFAULT_IMAGE_BASE64
import os
import shutil
import base64


def test_get_yml_type():
    from demisto_sdk.yaml_tools.extractor import Extractor
    configuration = Configuration()
    with patch.object(Extractor, '__init__', lambda a, b, c, d, e, f, g: None):
        extractor = Extractor('', '', False, False, '', configuration)
        # Test script case
        extractor.yml_type = ''
        extractor.yml_path = 'script'
        assert extractor.get_yml_type() == 'script'
        # Test integration case
        extractor.yml_type = ''
        extractor.yml_path = 'integration'
        assert extractor.get_yml_type() == 'integration'
        # Test error
        extractor.yml_type = ''
        extractor.yml_path = 'path'
        with raises(ValueError):
            extractor.get_yml_type()


def test_extract_long_description():
    from demisto_sdk.yaml_tools.extractor import Extractor
    configuration = Configuration()
    with patch.object(Extractor, '__init__', lambda a, b, c, d, e, f, g: None):
        # Test yml_type is script
        extractor = Extractor('', '', False, False, '', configuration)
        extractor.yml_type = ''
        extractor.yml_path = 'script'
        assert extractor.extract_long_description('output_path') is None
        # Test opening the file and writing to it
        extractor.yml_path = 'tests/test_files/integration-Zoom.yml'
        extractor.extract_long_description('tests/test_files/temp_file.txt')
        with open('tests/test_files/temp_file.txt', 'rb') as temp_file:
            file_data = temp_file.read().decode('utf-8')
            assert file_data == 'detaileddescription'
        os.remove('tests/test_files/temp_file.txt')


def test_extract_image():
    from demisto_sdk.yaml_tools.extractor import Extractor
    configuration = Configuration()
    with patch.object(Extractor, '__init__', lambda a, b, c, d, e, f, g: None):
        # Test yml_type is script
        extractor = Extractor('', '', False, False, '', configuration)
        extractor.yml_type = ''
        extractor.yml_path = 'script'
        assert extractor.extract_image('output_path') is None
        # Test opening the file and writing to it
        extractor.yml_path = 'tests/test_files/integration-Zoom.yml'
        extractor.extract_image('tests/test_files/temp_image.png')
        with open('tests/test_files/temp_image.png', 'rb') as temp_image:
            image_data = temp_image.read()
            image = base64.b64encode(image_data).decode('utf-8')
            assert image == DEFAULT_IMAGE_BASE64
        os.remove('tests/test_files/temp_image.png')


def test_extract_code():
    from demisto_sdk.yaml_tools.extractor import Extractor
    configuration = Configuration()
    with patch.object(Extractor, '__init__', lambda a, b, c, d, e, f, g: None):
        extractor = Extractor('', '', False, False, '', configuration)
        extractor.yml_type = ''
        extractor.common_server = True
        extractor.demisto_mock = True
        extractor.yml_path = 'tests/test_files/integration-Zoom.yml'
        extractor.dest_path = 'tests/test_files/temp_file.txt'
        extractor.extract_code('tests/test_files/temp_file.txt')
        with open('tests/test_files/temp_file.txt', 'rb') as temp_file:
            file_data = temp_file.read().decode('utf-8')
            assert 'import demistomock as demisto\n' in file_data
            assert 'from CommonServerPython import *\n' in file_data
            assert file_data[-1] == '\n'
        os.remove('tests/test_files/temp_file.txt')
        extractor.common_server = False
        extractor.demisto_mock = False
        extractor.extract_code('tests/test_files/temp_file.txt')
        with open('tests/test_files/temp_file.txt', 'rb') as temp_file:
            file_data = temp_file.read().decode('utf-8')
            assert 'import demistomock as demisto\n' not in file_data
            assert 'from CommonServerPython import *\n' not in file_data
            assert file_data[-1] == '\n'
        os.remove('tests/test_files/temp_file.txt')


def test_migrate():
    from demisto_sdk.yaml_tools.extractor import Extractor
    configuration = Configuration()
    yml_path = 'tests/test_files/integration-Zoom.yml'
    dest_path = 'tests/test_files/Zoom'
    extractor = Extractor(yml_path=yml_path, dest_path=dest_path, add_demisto_mock=True, add_common_server=True,
                          yml_type='', configuration=configuration)
    extractor.migrate()
    assert os.path.isdir('tests/test_files/Zoom')
    assert os.path.isfile('tests/test_files/Zoom/CHANGELOG.md')
    assert os.path.isfile('tests/test_files/Zoom/Pipfile')
    assert os.path.isfile('tests/test_files/Zoom/Pipfile.lock')
    assert os.path.isfile('tests/test_files/Zoom/Zoom.py')
    assert os.path.isfile('tests/test_files/Zoom/Zoom.yml')
    assert os.path.isfile('tests/test_files/Zoom/Zoom_description.md')
    assert os.path.isfile('tests/test_files/Zoom/Zoom_image.png')
    shutil.rmtree('tests/test_files/Zoom')
