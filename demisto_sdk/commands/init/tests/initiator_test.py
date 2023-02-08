import os
from collections import OrderedDict, deque
from os import listdir
from pathlib import Path
from typing import Callable

import pytest

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (
    INTEGRATION_CATEGORIES,
    MARKETPLACE_LIVE_DISCUSSIONS,
    MARKETPLACES,
    PACK_INITIAL_VERSION,
    PACK_SUPPORT_OPTIONS,
    XSOAR_AUTHOR,
    XSOAR_SUPPORT,
    XSOAR_SUPPORT_URL,
)
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.init.initiator import Initiator
from TestSuite.test_tools import ChangeCWD

json = JSON_Handler()
yaml = YAML_Handler()

DIR_NAME = "DirName"
PACK_NAME = "PackName"
PACK_DESC = "PackDesc"
PACK_SERVER_MIN_VERSION = "5.5.0"
PACK_AUTHOR = "PackAuthor"
PACK_URL = "https://www.github.com/pack"
PACK_EMAIL = "author@mail.com"
PACK_DEV_EMAIL = "author@mail.com"
PACK_TAGS = "Tag1,Tag2"
PACK_GITHUB_USERS = ""
INTEGRATION_NAME = "IntegrationName"
SCRIPT_NAME = "ScriptName"
DEFAULT_INTEGRATION = "BaseIntegration"
DEFAULT_SCRIPT = "BaseScript"


@pytest.fixture
def initiator():
    return Initiator("")


def generate_multiple_inputs(inputs: deque) -> Callable:
    def next_input(_):
        return inputs.popleft()

    return next_input


def raise_file_exists_error():
    raise FileExistsError


def test_get_created_dir_name(monkeypatch, initiator):
    monkeypatch.setattr("builtins.input", lambda _: DIR_NAME)
    initiator.get_created_dir_name("integration")
    assert initiator.dir_name == DIR_NAME


def test_get_object_id(monkeypatch, initiator):
    initiator.dir_name = DIR_NAME
    # test integration object with ID like dir name
    monkeypatch.setattr("builtins.input", lambda _: "Y")
    initiator.get_object_id("integration")
    assert initiator.id == DIR_NAME

    initiator.id = ""
    # test pack object with ID like dir name
    monkeypatch.setattr("builtins.input", lambda _: "Y")
    initiator.get_object_id("pack")
    assert initiator.id == DIR_NAME

    initiator.id = ""
    # test script object with ID different than dir name
    monkeypatch.setattr(
        "builtins.input", generate_multiple_inputs(deque(["N", "SomeIntegrationID"]))
    )
    initiator.get_object_id("script")
    assert initiator.id == "SomeIntegrationID"


def test_get_object_id_custom_name(monkeypatch, initiator):
    """Tests integration with custom name of id"""
    given_id = "given_id"
    monkeypatch.setattr("builtins.input", lambda _: given_id)
    initiator.is_pack_creation = False
    initiator.get_object_id("integration")
    assert given_id == initiator.id


class TestCreateMetadata:
    def test_create_metadata_non_filled_manually(self, initiator):
        """Create a non filled manually pack metadata

        Args:
            initiator (fixture): Initializes an instance of the 'Initiator' class

        Given
        - a non filled manually pack metadata.
        When
        - Creating the pack metadata file.
        Then
        - Ensure pack metadata is created with the expected attributes.
        """
        pack_metadata = initiator.create_metadata(False)
        assert pack_metadata == {
            "name": "## FILL MANDATORY FIELD ##",
            "description": "## FILL MANDATORY FIELD ##",
            "support": XSOAR_SUPPORT,
            "currentVersion": PACK_INITIAL_VERSION,
            "author": XSOAR_AUTHOR,
            "url": XSOAR_SUPPORT_URL,
            "email": "",
            "categories": [],
            "tags": [],
            "useCases": [],
            "keywords": [],
            "marketplaces": MARKETPLACES,
        }

    def test_create_metadata_non_filled_manually_with_data(self, initiator):
        """Create a non filled manually pack metadata updated with pre-existing data

        Args:
            initiator (fixture): Initializes an instance of the 'Initiator' class

        Given
        - a non filled manually pack metadata.
        - pre-existing data that should be included in the metadata
        When
        - Creating the pack metadata file.
        Then
        - Ensure pack metadata is created with the expected attributes.
        """
        name = "Test Pack"
        description = "Test Pack description"
        data = {"name": name, "description": description}
        pack_metadata = initiator.create_metadata(False, data)
        assert pack_metadata == {
            "name": name,
            "description": description,
            "support": XSOAR_SUPPORT,
            "currentVersion": PACK_INITIAL_VERSION,
            "author": XSOAR_AUTHOR,
            "url": XSOAR_SUPPORT_URL,
            "email": "",
            "categories": [],
            "tags": [],
            "useCases": [],
            "keywords": [],
            "marketplaces": MARKETPLACES,
        }

    def test_create_metadata_partner(self, monkeypatch, initiator):
        """Create a fake partner init inputs and test that it is converted to a metadata file correctly

        Args:
            monkeypatch (MagicMock): Patch of the user inputs
            initiator (fixture): Initializes an instance of the 'Initiator' class

        Given
        - init inputs of a partner supported packs.
        When
        - Creating the pack metadata file.
        Then
        - Ensure inputs are converted correctly to the pack metadata.
        """
        monkeypatch.setattr(
            "builtins.input",
            generate_multiple_inputs(
                deque(
                    [
                        PACK_NAME,
                        PACK_DESC,
                        "2",
                        "1",
                        "",
                        PACK_AUTHOR,
                        PACK_URL,
                        PACK_EMAIL,
                        PACK_DEV_EMAIL,
                        PACK_TAGS,
                        PACK_GITHUB_USERS,
                    ]
                )
            ),
        )
        pack_metadata = initiator.create_metadata(True)
        assert pack_metadata == {
            "author": PACK_AUTHOR,
            "categories": [INTEGRATION_CATEGORIES[0]],
            "currentVersion": "1.0.0",
            "description": PACK_DESC,
            "email": PACK_EMAIL,
            "devEmail": [PACK_DEV_EMAIL],
            "keywords": [],
            "name": PACK_NAME,
            "support": PACK_SUPPORT_OPTIONS[1],
            "tags": ["Tag1", "Tag2"],
            "url": PACK_URL,
            "useCases": [],
            "githubUser": [],
            "marketplaces": MARKETPLACES,
        }

    def test_create_metadata_partner_wrong_url(self, monkeypatch, initiator):
        """Create a fake partner init inputs and test that it is converted to a metadata file correctly

        Args:
            monkeypatch (MagicMock): Patch of the user inputs
            initiator (fixture): Initializes an instance of the 'Initiator' class

        Given
        - init inputs of a partner supported packs with a non valid PACK_URL(gave a value which does not contain http).
        When
        - Creating the pack metadata file.
        Then
        - Ensure inputs are converted correctly to the pack metadata.
        """
        monkeypatch.setattr(
            "builtins.input",
            generate_multiple_inputs(
                deque(
                    [
                        PACK_NAME,
                        PACK_DESC,
                        "2",
                        "1",
                        "xsoar",
                        PACK_AUTHOR,
                        "no_h[t][t]p",
                        PACK_URL,
                        PACK_EMAIL,
                        PACK_DEV_EMAIL,
                        PACK_TAGS,
                        PACK_GITHUB_USERS,
                    ]
                )
            ),
        )
        pack_metadata = initiator.create_metadata(True)
        assert pack_metadata == {
            "author": PACK_AUTHOR,
            "categories": [INTEGRATION_CATEGORIES[0]],
            "currentVersion": "1.0.0",
            "description": PACK_DESC,
            "email": PACK_EMAIL,
            "devEmail": [PACK_DEV_EMAIL],
            "keywords": [],
            "name": PACK_NAME,
            "support": PACK_SUPPORT_OPTIONS[1],
            "tags": ["Tag1", "Tag2"],
            "url": PACK_URL,
            "useCases": [],
            "githubUser": [],
            "marketplaces": ["xsoar"],
        }

    def test_create_metadata_community(self, monkeypatch, initiator):
        """Create a fake community init inputs and test that it is converted to a metadata file correctly

        Args:
            monkeypatch (MagicMock): Patch of the user inputs
            initiator (fixture): Initializes an instance of the 'Initiator' class

        Given
        - init inputs of a community supported packs.
        When
        - Creating the pack metadata file.
        Then
        - Ensure inputs are converted correctly to the pack metadata.
        """
        monkeypatch.setattr(
            "builtins.input",
            generate_multiple_inputs(
                deque(
                    [
                        PACK_NAME,
                        PACK_DESC,
                        "4",
                        "1",
                        "  marketplacev2",
                        PACK_AUTHOR,
                        PACK_DEV_EMAIL,
                        PACK_TAGS,
                        PACK_GITHUB_USERS,
                    ]
                )
            ),
        )
        pack_metadata = initiator.create_metadata(True)
        assert pack_metadata == {
            "author": PACK_AUTHOR,
            "categories": [INTEGRATION_CATEGORIES[0]],
            "currentVersion": "1.0.0",
            "description": PACK_DESC,
            "email": "",
            "devEmail": [PACK_DEV_EMAIL],
            "keywords": [],
            "name": PACK_NAME,
            "support": PACK_SUPPORT_OPTIONS[3],
            "tags": ["Tag1", "Tag2"],
            "url": MARKETPLACE_LIVE_DISCUSSIONS,
            "useCases": [],
            "githubUser": [],
            "marketplaces": ["marketplacev2"],
        }


def test_pack_init_without_filling_metadata(tmpdir, monkeypatch, initiator):
    """
    Given
        - Pack init inputs.
    When
        - Creating new pack without filling the metadata file.
    Then
        - Ensure it does not fail.
    """
    monkeypatch.setattr(
        "builtins.input", generate_multiple_inputs(deque(["PackName", "n", "n"]))
    )
    with ChangeCWD(tmpdir):
        result = initiator.init()
    assert result

    assert all(
        Path(tmpdir / initiator.full_output_path / d).exists()
        for d in initiator.DIR_LIST
    )


def test_get_valid_user_input(monkeypatch, initiator):
    monkeypatch.setattr(
        "builtins.input", generate_multiple_inputs(deque(["InvalidInput", "100", "1"]))
    )
    user_choice = initiator.get_valid_user_input(
        INTEGRATION_CATEGORIES, "Choose category"
    )
    assert user_choice == INTEGRATION_CATEGORIES[0]


def test_create_new_directory(mocker, monkeypatch, initiator):
    full_output_path = "path"
    initiator.full_output_path = full_output_path

    # create new dir successfully
    mocker.patch.object(os, "mkdir", return_value=None)
    assert initiator.create_new_directory()

    mocker.patch.object(os, "mkdir", side_effect=FileExistsError)
    # override dir successfully
    monkeypatch.setattr("builtins.input", lambda _: "Y")
    with pytest.raises(FileExistsError):
        assert initiator.create_new_directory()

    # fail to create pack cause of existing dir without overriding it
    monkeypatch.setattr("builtins.input", lambda _: "N")
    assert initiator.create_new_directory() is False


def test_yml_reformatting(monkeypatch, tmp_path, initiator):
    monkeypatch.setattr("builtins.input", generate_multiple_inputs(deque(["6.0.0"])))
    integration_id = "HelloWorld"
    initiator.id = integration_id
    initiator.category = "Utilities"
    d = tmp_path / integration_id
    d.mkdir()
    full_output_path = Path(d)
    initiator.full_output_path = full_output_path

    p = d / f"{integration_id}.yml"
    with p.open(mode="w") as f:
        yaml.dump({"commonfields": {"id": ""}, "name": "", "display": ""}, f)
    dir_name = "HelloWorldTest"
    initiator.dir_name = dir_name
    initiator.yml_reformatting(
        current_suffix=initiator.HELLO_WORLD_INTEGRATION, integration=True
    )
    with open(full_output_path / f"{dir_name}.yml") as f:
        yml_dict = yaml.load(f)
        assert yml_dict == OrderedDict(
            {
                "commonfields": OrderedDict({"id": "HelloWorld"}),
                "display": "HelloWorld",
                "name": "HelloWorld",
                "fromversion": "6.0.0",
                "category": "Utilities",
            }
        )


SCRIPT_TEMPLATE_DATA = """
    def main():
    try:
        return_results(say_hello_command(demisto.args()))
    except Exception as ex:
        demisto.error(traceback.format_exc())  # print the traceback
        return_error(f'Failed to execute BaseScript. Error: {str(ex)}')
    """
SCRIPT_EXPECTED_DATA = """
    def main():
    try:
        return_results(say_hello_command(demisto.args()))
    except Exception as ex:
        demisto.error(traceback.format_exc())  # print the traceback
        return_error(f'Failed to execute MyTest. Error: {str(ex)}')
    """


def test_change_template_name_script_py(monkeypatch, tmp_path, initiator):
    """
    Tests change_template_name_script_py function.
    Given
        - Script template file
    When
        - Initiating an script
    Then
        - Ensure all template names appearances will change to the real script name.
    """
    monkeypatch.setattr("builtins.input", generate_multiple_inputs(deque(["6.0.0"])))
    script_id = "MyTest"
    initiator.id = script_id
    initiator.category = "Utilities"
    d = tmp_path / script_id
    d.mkdir()
    full_output_path = Path(d)
    initiator.full_output_path = full_output_path
    p = d / f"{script_id}.py"
    with p.open(mode="w") as f:
        f.write(SCRIPT_TEMPLATE_DATA)
    dir_name = "MyTest"
    initiator.dir_name = dir_name
    initiator.change_template_name_script_py(
        current_suffix=dir_name, current_template="BaseScript"
    )

    with open(full_output_path / f"{dir_name}.py") as f:
        new_data = f.read()
        assert new_data == SCRIPT_EXPECTED_DATA


def test_get_remote_templates__valid(mocker, initiator):
    """
    Tests get_remote_template function.
    Configures mocker instance and patches the tools's get_remote_file to return a file content.

    Given
        - A list of files to download from remote repo
    When
        - Initiating an object - Script or Integration
    Then
        - Ensure file with Test.py name was created in PackName folder
        - Ensure the file's content is the same as the one we got from get_remote_file return value
    """
    mocker.patch.object(tools, "get_remote_file", return_value=b"Test im in file")
    initiator.full_output_path = PACK_NAME
    os.makedirs(PACK_NAME, exist_ok=True)
    res = initiator.get_remote_templates(["Test.py"], dir=DIR_NAME)
    file_path = os.path.join(PACK_NAME, "Test.py")
    with open(file_path) as f:
        file_content = f.read()

    assert res
    assert "Test im in file" in file_content

    os.remove(os.path.join(PACK_NAME, "Test.py"))
    os.rmdir(PACK_NAME)


def test_get_remote_templates__invalid(mocker, initiator):
    """
    Tests get_remote_template function.
    Configures mocker instance and patches the tools's get_remote_file to return an empty file content.

    Given
        - An unreachable file to download from remote repo
    When
        - Initiating an object - Script or Integration
    Then
        - Ensure get_remote_templates returns False and doesn't raise an exception
    """
    mocker.patch.object(tools, "get_remote_file", return_value={})
    initiator.full_output_path = PACK_NAME
    os.makedirs(PACK_NAME, exist_ok=True)
    res = initiator.get_remote_templates(["Test.py"], dir=DIR_NAME)

    assert not res

    os.remove(os.path.join(PACK_NAME, "Test.py"))
    os.rmdir(PACK_NAME)


def test_integration_init(monkeypatch, initiator, tmpdir):
    """
    Tests `integration_init` function.

    Given
        - Inputs to init integration in a given output.

    When
        - Running the init command.

    Then
        - Ensure the function's return value is True
        - Ensure integration directory with the desired integration name is created successfully.
        - Ensure integration directory contain all files of the Boilerplate template.
    """
    monkeypatch.setattr("builtins.input", generate_multiple_inputs(deque(["6.0.0"])))
    temp_pack_dir = os.path.join(tmpdir, PACK_NAME)
    os.makedirs(temp_pack_dir, exist_ok=True)

    initiator.output = temp_pack_dir
    initiator.dir_name = INTEGRATION_NAME
    initiator.is_integration = True
    initiator.template = DEFAULT_INTEGRATION
    initiator.category = "Utilities"

    integration_path = os.path.join(temp_pack_dir, INTEGRATION_NAME)
    res = initiator.integration_init()
    integration_dir_files = {file for file in listdir(integration_path)}
    expected_files = {
        "Pipfile",
        "Pipfile.lock",
        "command_examples",
        "test_data",
        "README.md",
        f"{INTEGRATION_NAME}.py",
        f"{INTEGRATION_NAME}.yml",
        f"{INTEGRATION_NAME}_description.md",
        f"{INTEGRATION_NAME}_test.py",
        f"{INTEGRATION_NAME}_image.png",
    }

    assert res
    assert os.path.isdir(integration_path)
    assert expected_files == integration_dir_files


@pytest.mark.parametrize("template", ["HelloWorld", "FeedHelloWorld"])
def test_template_integration_init(initiator, tmpdir, monkeypatch, mocker, template):
    """
    Tests `integration_init` function with a given integration template name.

    Given
        - Two Integration templates - HelloWorld, FeedHelloWorld.

    When
        - Running the init command without secrets ignore.

    Then
        - Ensure the function's return value is True
        - Ensure integration directory with the desired integration name is created successfully.
        - Ensure integration directory contains all the files of the template integration.
        - Ensure .secrets-ignore file is not created.
    """
    monkeypatch.setattr(
        "builtins.input", generate_multiple_inputs(deque(["6.0.0", "n"]))
    )
    white_list = {"files": [], "iocs": {}, "generic_strings": []}
    temp_test_dir = os.path.join(tmpdir, "Tests")
    os.makedirs(temp_test_dir, exist_ok=True)
    with open(f"{temp_test_dir}/secrets_white_list.json", "w") as f:
        json.dump(white_list, f)

    temp_pack_dir = os.path.join(tmpdir, "Packs", PACK_NAME)
    os.makedirs(temp_pack_dir, exist_ok=True)
    secrets_ignore_path = f"{temp_pack_dir}/.secrets-ignore"

    initiator.output = temp_pack_dir
    initiator.dir_name = INTEGRATION_NAME
    initiator.is_integration = True
    initiator.template = template
    initiator.category = "Utilities"
    mocker.patch(
        "demisto_sdk.commands.init.initiator.get_pack_name", return_value="PackName"
    )

    integration_path = os.path.join(temp_pack_dir, INTEGRATION_NAME)

    with ChangeCWD(tmpdir):
        res = initiator.integration_init()

    integration_dir_files = set(listdir(integration_path))
    expected_files = {
        "Pipfile",
        "Pipfile.lock",
        "README.md",
        f"{INTEGRATION_NAME}.py",
        f"{INTEGRATION_NAME}.yml",
        f"{INTEGRATION_NAME}_description.md",
        f"{INTEGRATION_NAME}_test.py",
        f"{INTEGRATION_NAME}_image.png",
        "test_data",
        "command_examples",
    }

    assert res
    assert os.path.isdir(integration_path)
    diff = expected_files.difference(integration_dir_files)
    assert not diff, f"There's a missing file in the copied files, diff is {diff}"
    assert not os.path.exists(secrets_ignore_path)


@pytest.mark.parametrize("template", ["HelloWorld", "FeedHelloWorld"])
def test_integration_init_with_ignore_secrets(
    initiator, tmpdir, monkeypatch, mocker, template
):
    """
    Tests `integration_init` function with a given script template name.
    Given
        - Two Integration templates - HelloWorld, FeedHelloWorld.
    When
        - Running the init command with secrets ignore.
    Then
        - Ensure the function's ('integration_init') return value is True
        - Ensure integration directory with the desired integration name is created successfully.
        - Ensure integration directory contain all files.
        - Ensure .secrets-ignore file is not empty.
    """
    monkeypatch.setattr(
        "builtins.input", generate_multiple_inputs(deque(["6.0.0", "y"]))
    )
    white_list = {"files": [], "iocs": {}, "generic_strings": []}
    temp_test_dir = os.path.join(tmpdir, "Tests")
    os.makedirs(temp_test_dir, exist_ok=True)
    with open(f"{temp_test_dir}/secrets_white_list.json", "w") as f:
        json.dump(white_list, f)

    temp_pack_dir = os.path.join(tmpdir, "Packs", PACK_NAME)
    os.makedirs(temp_pack_dir, exist_ok=True)
    secrets_ignore_path = f"{temp_pack_dir}/.secrets-ignore"

    initiator.output = temp_pack_dir
    initiator.dir_name = INTEGRATION_NAME
    initiator.is_integration = True
    initiator.template = template
    initiator.category = "Utilities"
    mocker.patch(
        "demisto_sdk.commands.init.initiator.get_pack_name", return_value="PackName"
    )

    integration_path = os.path.join(temp_pack_dir, INTEGRATION_NAME)

    with ChangeCWD(tmpdir):
        res = initiator.integration_init()

    integration_dir_files = set(listdir(integration_path))
    expected_files = {
        "Pipfile",
        "Pipfile.lock",
        "README.md",
        f"{INTEGRATION_NAME}.py",
        f"{INTEGRATION_NAME}.yml",
        f"{INTEGRATION_NAME}_description.md",
        f"{INTEGRATION_NAME}_test.py",
        f"{INTEGRATION_NAME}_image.png",
        "test_data",
        "command_examples",
    }

    assert res
    assert os.path.isdir(integration_path)
    diff = expected_files.difference(integration_dir_files)
    assert (
        not diff
    ), f"There are missing file's in the files you expected to create, The missing file's are {diff}"
    assert os.stat(secrets_ignore_path).st_size > 0


def test_script_init(initiator, tmpdir, monkeypatch, mocker):
    """
    Tests `script_init` function.

    Given
        - Inputs to init script in a given output.

    When
        - Running the init command.

    Then
        - Ensure the function's return value is True
        - Ensure script directory with the desired script name is created successfully.
        - Ensure script directory contain all files.
        - Ensure .secrets-ignore file is not created.
    """
    monkeypatch.setattr(
        "builtins.input", generate_multiple_inputs(deque(["6.0.0", "n"]))
    )
    white_list = {"files": [], "iocs": {}, "generic_strings": []}
    temp_test_dir = os.path.join(tmpdir, "Tests")
    os.makedirs(temp_test_dir, exist_ok=True)
    with open(f"{temp_test_dir}/secrets_white_list.json", "w") as f:
        json.dump(white_list, f)

    temp_pack_dir = os.path.join(tmpdir, "Packs", PACK_NAME)
    os.makedirs(temp_pack_dir, exist_ok=True)
    secrets_ignore_path = f"{temp_pack_dir}/.secrets-ignore"

    initiator.template = DEFAULT_SCRIPT
    initiator.dir_name = SCRIPT_NAME
    initiator.output = temp_pack_dir
    script_path = os.path.join(temp_pack_dir, SCRIPT_NAME)
    mocker.patch(
        "demisto_sdk.commands.init.initiator.get_pack_name", return_value="PackName"
    )

    with ChangeCWD(tmpdir):
        res = initiator.script_init()

    script_dir_files = set(listdir(script_path))
    expected_files = {
        f"{SCRIPT_NAME}.py",
        f"{SCRIPT_NAME}.yml",
        f"{SCRIPT_NAME}_test.py",
        "README.md",
        "test_data",
    }
    diff = expected_files.difference(script_dir_files)

    assert res
    assert os.path.isdir(script_path)
    assert (
        not diff
    ), f"There are missing file's in the files you expected to create, The missing file's are {diff}"
    assert not os.path.exists(secrets_ignore_path)


def test_script_init_with_ignore_secrets(initiator, tmpdir, monkeypatch, mocker):
    """
    Tests `script_init` function with a given script template name.
    Given
        - A script template - BaseScript.
    When
        - Running the init command with secrets ignore.
    Then
        - Ensure the function's ('script_init') return value is True
        - Ensure script directory with the desired script name is created successfully.
        - Ensure script directory contain all files.
        - Ensure .secrets-ignore file is not empty.
    """
    monkeypatch.setattr(
        "builtins.input", generate_multiple_inputs(deque(["6.0.0", "y"]))
    )
    white_list = {"files": [], "iocs": {}, "generic_strings": []}
    temp_test_dir = os.path.join(tmpdir, "Tests")
    os.makedirs(temp_test_dir, exist_ok=True)
    with open(f"{temp_test_dir}/secrets_white_list.json", "w") as f:
        json.dump(white_list, f)

    temp_pack_dir = os.path.join(tmpdir, "Packs", PACK_NAME)
    os.makedirs(temp_pack_dir, exist_ok=True)
    secrets_ignore_path = f"{temp_pack_dir}/.secrets-ignore"

    initiator.template = DEFAULT_SCRIPT
    initiator.dir_name = SCRIPT_NAME
    initiator.output = temp_pack_dir
    script_path = os.path.join(temp_pack_dir, SCRIPT_NAME)
    mocker.patch(
        "demisto_sdk.commands.init.initiator.get_pack_name", return_value="PackName"
    )

    with ChangeCWD(tmpdir):
        res = initiator.script_init()

    script_dir_files = set(listdir(script_path))
    expected_files = {
        f"{SCRIPT_NAME}.py",
        f"{SCRIPT_NAME}.yml",
        f"{SCRIPT_NAME}_test.py",
        "README.md",
        "test_data",
    }
    diff = expected_files.difference(script_dir_files)

    assert res
    assert os.path.isdir(script_path)
    assert (
        not diff
    ), f"There are missing file's in the files you expected to create, The missing file's are {diff}"
    assert os.stat(secrets_ignore_path).st_size > 0
