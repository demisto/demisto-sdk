import pytest
from mock import patch
import yaml
import base64


def test_clean_python_code():
    from demisto_sdk.yaml_tools.unifier import Unifier
    unifier = Unifier("path")
    script_code = "import demistomock as demistofrom CommonServerPython import *" \
                  "from CommonServerUserPython import *from __future__ import print_function"
    # Test remove_print_future is False
    script_code = unifier.clean_python_code(script_code, remove_print_future=False)
    assert script_code == "from __future__ import print_function"
    # Test remove_print_future is True
    script_code = unifier.clean_python_code(script_code)
    assert script_code == ""


def test_get_code_file():
    from demisto_sdk.yaml_tools.unifier import Unifier
    # Test integration case
    unifier = Unifier("tests/test_files/VulnDB/")
    assert unifier.get_code_file(".py") == "tests/test_files/VulnDB/VulnDB.py"
    unifier = Unifier("tests/test_files")
    with pytest.raises(Exception):
        unifier.get_code_file(".py")
    # Test script case
    unifier = Unifier("tests/test_files/CalculateGeoDistance/")
    assert unifier.get_code_file(".py") == "tests/test_files/CalculateGeoDistance/CalculateGeoDistance.py"


def test_get_script_package_data():
    from demisto_sdk.yaml_tools.unifier import Unifier
    unifier = Unifier("tests/")
    with pytest.raises(Exception):
        unifier.get_script_package_data()
    unifier = Unifier("tests/test_files/CalculateGeoDistance")
    with open("tests/test_files/CalculateGeoDistance/CalculateGeoDistance.py", "r") as code_file:
        code = code_file.read()
    yml_path, code_data = unifier.get_script_package_data()
    assert yml_path == "tests/test_files/CalculateGeoDistance/CalculateGeoDistance.yml"
    assert code_data == code


def test_get_data():
    from demisto_sdk.yaml_tools.unifier import Unifier
    with patch.object(Unifier, "__init__", lambda a, b, c, d, e, f, g: None):
        unifier = Unifier(None, None, None, None, None, None)
        unifier.package_path = "tests/test_files/VulnDB/"
        unifier.dir_name = "Integrations"
        with open("tests/test_files/VulnDB/VulnDB_image.png", "rb") as image_file:
            image = image_file.read()
        data, found_data_path = unifier.get_data("*png")
        assert data == image
        assert found_data_path == "tests/test_files/VulnDB/VulnDB_image.png"
        unifier.dir_name = "Scripts"
        data, found_data_path = unifier.get_data("*png")
        assert data is None
        assert found_data_path is None


def test_insert_description_to_yml():
    from demisto_sdk.yaml_tools.unifier import Unifier
    with patch.object(Unifier, "__init__", lambda a, b, c, d, e, f, g: None):
        unifier = Unifier(None, None, None, None, None, None)
        unifier.package_path = "tests/test_files/VulnDB/"
        unifier.dir_name = "Integrations"
        with open("tests/test_files/VulnDB/VulnDB_description.md", "rb") as desc_file:
            desc_data = desc_file.read().decode("utf-8")
            desc_data = '|\n  ' + desc_data.replace('\n', '\n  ')
        yml_text, found_data_path = unifier.insert_description_to_yml({}, "")
        assert found_data_path == "tests/test_files/VulnDB/VulnDB_description.md"
        assert desc_data in yml_text


def test_insert_image_to_yml():
    from demisto_sdk.yaml_tools.unifier import Unifier
    with patch.object(Unifier, "__init__", lambda a, b, c, d, e, f, g: None):
        unifier = Unifier(None, None, None, None, None, None)
        unifier.package_path = "tests/test_files/VulnDB/"
        unifier.dir_name = "Integrations"
        unifier.image_prefix = "data:image/png;base64,"
        with open("tests/test_files/VulnDB/VulnDB_image.png", "rb") as image_file:
            image_data = image_file.read()
            image_data = unifier.image_prefix + base64.b64encode(image_data).decode('utf-8')
        with open("tests/test_files/VulnDB/VulnDB.yml", mode="r", encoding="utf-8") as yml_file:
            yml_text_test = yml_file.read()
        with open("tests/test_files/VulnDB/VulnDB.yml", "r") as yml:
            yml_data = yaml.safe_load(yml)
        yml_text, found_img_path = unifier.insert_image_to_yml(yml_data, yml_text_test)
        yml_text_test = 'image: ' + image_data + '\n' + yml_text_test
        assert found_img_path == "tests/test_files/VulnDB/VulnDB_image.png"
        assert yml_text == yml_text_test


@pytest.mark.parametrize('package_path, dir_name, file_path', [
    ("tests/test_files/VulnDB/", "Integrations", "tests/test_files/VulnDB/VulnDB"),
    ("tests/test_files/CalculateGeoDistance/", "Scripts",
     "tests/test_files/CalculateGeoDistance/CalculateGeoDistance")])
def test_insert_script_to_yml(package_path, dir_name, file_path):
    from demisto_sdk.yaml_tools.unifier import Unifier
    with patch.object(Unifier, "__init__", lambda a, b, c, d, e, f, g: None):
        unifier = Unifier("", None, None, None, None, None)
        unifier.package_path = package_path
        unifier.dir_name = dir_name
        with open(file_path + ".yml", mode="r", encoding="utf-8") as yml_file:
            test_yml_text = yml_file.read()
        with open(file_path + ".yml", "r") as yml:
            test_yml_data = yaml.safe_load(yml)

        yml_text, script_path = unifier.insert_script_to_yml(".py", test_yml_text, test_yml_data)

        with open(file_path + ".py", mode="r", encoding="utf-8") as script_file:
            script_code = script_file.read()
        clean_code = unifier.clean_python_code(script_code)
        lines = ['|-']
        lines.extend(u'    {}'.format(line) for line in clean_code.split('\n'))
        script_code = u'\n'.join(lines)
        test_yml_text = test_yml_text.replace("script: ''", "script: " + script_code)
        test_yml_text = test_yml_text.replace("script: '-'", "script: " + script_code)

        assert yml_text == test_yml_text
        assert script_path == file_path + ".py"


@pytest.mark.parametrize('package_path, dir_name, file_path', [
    ("tests/test_files/VulnDB/", "Integrations", "tests/test_files/VulnDB/VulnDB"),
    ("tests/test_files/CalculateGeoDistance/", "Scripts",
     "tests/test_files/CalculateGeoDistance/CalculateGeoDistance"),
    ("tests/test_files/VulnDB/", "fake_directory", "tests/test_files/VulnDB/VulnDB")])
def test_insert_script_to_yml_exceptions(package_path, dir_name, file_path):
    from demisto_sdk.yaml_tools.unifier import Unifier
    with patch.object(Unifier, "__init__", lambda a, b, c, d, e, f, g: None):
        unifier = Unifier("", None, None, None, None, None)
        unifier.package_path = package_path
        unifier.dir_name = dir_name
        with open(file_path + ".yml", "r") as yml:
            test_yml_data = yaml.safe_load(yml)
        if dir_name == "Scripts":
            test_yml_data['script'] = 'blah'
        elif dir_name == "Integrations":
            test_yml_data['script']['script'] = 'blah'

        with pytest.raises(ValueError):
            unifier.insert_script_to_yml(".py", "", test_yml_data)
