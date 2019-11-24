from pytest import raises
from mock import patch
import yaml
import base64


def test_clean_python_code():
    from demisto_sdk.yaml_tools.unifier import Unifier
    unifier = Unifier("path")
    script_code = "import demistomock as demistofrom CommonServerPython import *" \
                  "from CommonServerUserPython import *from __future__ import print_function"
    script_code = unifier.clean_python_code(script_code, remove_print_future=False)
    assert script_code == "from __future__ import print_function"
    script_code = unifier.clean_python_code(script_code)
    assert script_code == ""


def test_get_code_file():
    from demisto_sdk.yaml_tools.unifier import Unifier
    unifier = Unifier("tests/test_files/VulnDB/")
    assert unifier.get_code_file(".py") == "tests/test_files/VulnDB/VulnDB.py"
    unifier = Unifier("tests/test_files")
    with raises(Exception):
        unifier.get_code_file(".py")


def test_get_script_package_data():
    from demisto_sdk.yaml_tools.unifier import Unifier
    unifier = Unifier("tests/")
    with raises(Exception):
        unifier.get_script_package_data()
    unifier = Unifier("tests/test_files/VulnDB/")
    with open("tests/test_files/VulnDB/VulnDB.py", "r") as code_file:
        code = code_file.read()
    yml_path, code_data = unifier.get_script_package_data()
    assert yml_path == "tests/test_files/VulnDB/VulnDB.yml"
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
