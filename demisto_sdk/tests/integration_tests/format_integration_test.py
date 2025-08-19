from pathlib import Path, PosixPath
from typing import List

import pytest
from typer.testing import CliRunner

from demisto_sdk.__main__ import app
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (
    GENERAL_DEFAULT_FROMVERSION,
)
from demisto_sdk.commands.common.content.content import Content
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.hook_validations.integration import (
    IntegrationValidator,
)
from demisto_sdk.commands.common.hook_validations.playbook import PlaybookValidator
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.tools import get_dict_from_file, is_test_config_match
from demisto_sdk.commands.format import format_module, update_generic
from demisto_sdk.commands.format.update_generic import BaseUpdate
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
from demisto_sdk.commands.format.update_playbook import PlaybookYMLFormat
from demisto_sdk.commands.validate.old_validate_manager import OldValidateManager
from demisto_sdk.tests.constants_test import (
    DESTINATION_FORMAT_INTEGRATION_COPY,
    DESTINATION_FORMAT_PLAYBOOK_COPY,
    INTEGRATION_WITH_TEST_PLAYBOOKS,
    PLAYBOOK_WITH_TEST_PLAYBOOKS,
    SOURCE_FORMAT_INTEGRATION_COPY,
    SOURCE_FORMAT_PLAYBOOK_COPY,
)
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    GENERIC_DEFINITION,
    GENERIC_FIELD,
    GENERIC_MODULE,
    GENERIC_TYPE,
)
from TestSuite.test_tools import ChangeCWD

excluded_files = [
    "CommonServerPython.py",
    "demistomock.py",
    "CommonServerUserPython.py",
    "conftest.py",
    ".venv",
]


with open(SOURCE_FORMAT_INTEGRATION_COPY) as of:
    SOURCE_FORMAT_INTEGRATION_YML = (
        of.read()
    )  # prevents overriding by other `format` calls.
with open(SOURCE_FORMAT_PLAYBOOK_COPY) as of:
    SOURCE_FORMAT_PLAYBOOK_YML = (
        of.read()
    )  # prevents overriding by other `format` calls.
BASIC_YML_CONTENTS = (SOURCE_FORMAT_INTEGRATION_YML, SOURCE_FORMAT_PLAYBOOK_YML)

BASIC_YML_TEST_PACKS = [
    (
        SOURCE_FORMAT_INTEGRATION_COPY,
        DESTINATION_FORMAT_INTEGRATION_COPY,
        IntegrationYMLFormat,
        "New Integration_copy",
        "integration",
    ),
    (
        SOURCE_FORMAT_PLAYBOOK_COPY,
        DESTINATION_FORMAT_PLAYBOOK_COPY,
        PlaybookYMLFormat,
        "File Enrichment-GenericV2_copy",
        "playbook",
    ),
]

YML_FILES_WITH_TEST_PLAYBOOKS = [
    (
        INTEGRATION_WITH_TEST_PLAYBOOKS,
        DESTINATION_FORMAT_INTEGRATION_COPY,
        IntegrationYMLFormat,
        "New Integration",
        "integration",
    ),
    (
        PLAYBOOK_WITH_TEST_PLAYBOOKS,
        DESTINATION_FORMAT_PLAYBOOK_COPY,
        PlaybookYMLFormat,
        "File Enrichment-GenericV2_copy",
        "playbook",
    ),
]
FORMAT_CMD = "format"
CONF_JSON_ORIGINAL_CONTENT = {
    "tests": [
        {"integrations": "PagerDuty v2", "playbookID": "PagerDuty Test"},
        {"integrations": "Account Enrichment", "playbookID": "PagerDuty Test"},
        {"integrations": "TestCreateDuplicates", "playbookID": "PagerDuty Test"},
    ]
}


@pytest.fixture(autouse=True)
def set_git_test_env(mocker):
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value=True)
    mocker.patch.object(Content, "git_util", return_value=GitUtil())
    mocker.patch.object(
        OldValidateManager, "setup_prev_ver", return_value="origin/master"
    )
    mocker.patch.object(GitUtil, "_is_file_git_ignored", return_value=False)


@pytest.mark.parametrize("source_yml", BASIC_YML_CONTENTS)
def test_integration_format_yml_with_no_test_positive(
    mocker, tmp_path: PosixPath, source_yml: str
):
    """
    Given
    - A yml file (integration, playbook or script) with no 'tests' configured

    When
    - Entering '-at' so the prompt message about asking the user if he wants to add 'No tests' to the file will
        appear.
    - Entering 'Y' into the prompt message about that asks the user if he wants to add 'No tests' to the file

    Then
    -  Ensure no exception is raised
    -  Ensure 'No tests' is added in the first time
    -  Ensure message is not prompt in the second time
    """

    source_file, output_file = tmp_path / "source.yml", tmp_path / "output.yml"
    source_path, output_path = str(source_file), str(output_file)
    source_file.write_text(source_yml)
    mocker.patch.object(BaseUpdate, "set_fromVersion")
    # Running format in the first time
    runner = CliRunner()
    with ChangeCWD(tmp_path):
        first_run_result = runner.invoke(
            app,
            [FORMAT_CMD, "-i", source_path, "-o", output_path, "-at", "-ngr"],
            input="Y",
        )
    assert not first_run_result.exception
    output_yml = get_dict_from_file(output_path)
    assert output_yml[0].get("tests") == ["No tests (auto formatted)"]
    message = f'Formatting {output_file} with "No tests"'
    assert message in first_run_result.output

    # Running format for the second time should raise no exception and should raise no prompt to the user
    second_run_result = runner.invoke(
        app, [FORMAT_CMD, "-i", output_path, "-y", "-ngr"]
    )
    assert second_run_result.exit_code == 0
    assert not second_run_result.exception


@pytest.mark.parametrize("source_yml", BASIC_YML_CONTENTS)
def test_integration_format_yml_with_no_test_negative(
    mocker, monkeypatch, tmp_path: PosixPath, source_yml: str
):
    """
    Given
    - A yml file (integration, playbook or script) with no 'tests' configured

    When
    - Entering '-at' so the prompt message about asking the user if he wants to add 'No tests' to the file will
        appear.
    - Entering 'N' into the prompt message about that asks the user if he wants to add 'No tests' to the file

    Then
    -  Ensure no exception is raised
    -  Ensure 'No tests' is not added
    """

    source_file, output_file = tmp_path / "source.yml", tmp_path / "output.yml"
    source_path, output_path = str(source_file), str(output_file)
    source_file.write_text(source_yml)
    mocker.patch.object(BaseUpdate, "set_default_from_version", return_value=None)

    runner = CliRunner()
    mocker.patch("builtins.input", return_value="y")
    with ChangeCWD(tmp_path):
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-i",
                source_path,
                "-o",
                output_path,
                "-at",
                "-ngr",
                "--console-log-threshold",
                "DEBUG",
            ],
            input="N",
        )
    assert not result.exception
    assert f'Not formatting {source_path} with "No tests"' in result.output
    yml_content = get_dict_from_file(output_path)
    assert not yml_content[0].get("tests")


@pytest.mark.parametrize("source_yml", BASIC_YML_CONTENTS)
def test_integration_format_yml_with_no_test_no_interactive_positive(
    mocker, tmp_path: PosixPath, source_yml: str
):
    """
    Given
    - A yml file (integration, playbook or script) with no 'tests' configured

    When
    - using the '-y' option

    Then
    -  Ensure no exception is raised
    -  Ensure 'No tests' is added in the first time
    """
    source_file, output_file = tmp_path / "source.yml", tmp_path / "output.yml"
    source_path, output_path = str(source_file), str(output_file)
    source_file.write_text(source_yml)

    runner = CliRunner()
    # Running format in the first time
    with ChangeCWD(tmp_path):
        result = runner.invoke(
            app, [FORMAT_CMD, "-i", source_path, "-o", output_path, "-y", "-ngr"]
        )
    assert not result.exception
    yml_content = get_dict_from_file(output_path)
    assert yml_content[0].get("tests") == ["No tests (auto formatted)"]


@pytest.mark.parametrize(
    "source_path,destination_path,formatter,yml_title,file_type",
    YML_FILES_WITH_TEST_PLAYBOOKS,
)
def test_integration_format_configuring_conf_json_no_interactive_positive(
    mocker,
    tmp_path: PosixPath,
    source_path: str,
    destination_path: str,
    formatter: BaseUpdateYML,
    yml_title: str,
    file_type: str,
):
    """
    Given
    - A yml file (integration, playbook or script) with no tests playbooks configured that are not configured
        in conf.json

    When
    - using the -y option

    Then
    -  Ensure no exception is raised
    -  If file_type is playbook or a script: Ensure {"playbookID": <content item ID>} is added to conf.json
        for each test playbook configured in the yml under 'tests' key
    -  If file_type is integration: Ensure {"playbookID": <content item ID>, "integrations": yml_title} is
        added to conf.json for each test playbook configured in the yml under 'tests' key
    """
    # Setting up conf.json
    conf_json_path = tmp_path / "conf.json"
    mocker.patch(
        "demisto_sdk.commands.format.update_generic_yml.CONF_PATH", conf_json_path
    )
    with open(conf_json_path, "w") as file:
        json.dump(CONF_JSON_ORIGINAL_CONTENT, file, indent=4)

    test_playbooks = ["test1", "test2"]
    saved_file_path = str(tmp_path / Path(destination_path).name)
    runner = CliRunner()
    # Running format in the first time
    result = runner.invoke(
        app, [FORMAT_CMD, "-i", source_path, "-o", saved_file_path, "-y", "-ngr"]
    )
    assert not result.exception
    if file_type == "playbook":
        _verify_conf_json_modified(test_playbooks, "", conf_json_path)
    else:
        _verify_conf_json_modified(test_playbooks, yml_title, conf_json_path)


@pytest.mark.parametrize(
    "source_path,destination_path,formatter,yml_title,file_type",
    YML_FILES_WITH_TEST_PLAYBOOKS,
)
def test_integration_format_configuring_conf_json_positive(
    mocker,
    tmp_path: PosixPath,
    source_path: str,
    destination_path: str,
    formatter: BaseUpdateYML,
    yml_title: str,
    file_type: str,
):
    """
    Given
    - A yml file (integration, playbook or script) with no tests playbooks configured that are not configured
        in conf.json

    When
    - Entering 'Y' into the prompt message that asks the user if he wants to configure those test playbooks into
        conf.json

    Then
    -  Ensure no exception is raised
    -  If file_type is playbook or a script: Ensure {"playbookID": <content item ID>} is added to conf.json
        for each test playbook configured in the yml under 'tests' key
    -  If file_type is integration: Ensure {"playbookID": <content item ID>, "integrations": yml_title} is
        added to conf.json for each test playbook configured in the yml under 'tests' key
    -  Ensure message is not prompt in the second time
    """

    # Setting up conf.json
    conf_json_path = tmp_path / "conf.json"
    mocker.patch(
        "demisto_sdk.commands.format.update_generic_yml.CONF_PATH", conf_json_path
    )
    with open(conf_json_path, "w") as file:
        json.dump(CONF_JSON_ORIGINAL_CONTENT, file, indent=4)
    mocker.patch.object(BaseUpdate, "set_default_from_version", return_value=None)

    test_playbooks = ["test1", "test2"]
    saved_file_path = str(tmp_path / Path(destination_path).name)
    runner = CliRunner()
    # Running format in the first time
    with ChangeCWD(tmp_path):
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-i",
                source_path,
                "-o",
                saved_file_path,
                "--assume-yes",
                "-ngr",
            ],
            input="Y",
        )
    assert not result.exception
    assert "Added test playbooks to conf.json successfully" in result.output
    assert "No unconfigured test playbooks" not in result.output
    if file_type == "playbook":
        _verify_conf_json_modified(test_playbooks, "", conf_json_path)
    else:
        _verify_conf_json_modified(test_playbooks, yml_title, conf_json_path)
    # Running format for the second time should raise no exception and should raise no prompt to the user
    result = runner.invoke(
        app,
        [
            FORMAT_CMD,
            "-i",
            saved_file_path,
            "-ngr",
            "--console-log-threshold",
            "DEBUG",
        ],
        input="Y",
    )
    assert not result.exception
    assert "No unconfigured test playbooks" in result.output


@pytest.mark.parametrize(
    "source_path,destination_path,formatter,yml_title,file_type",
    YML_FILES_WITH_TEST_PLAYBOOKS,
)
def test_integration_format_configuring_conf_json_negative(
    mocker,
    tmp_path: PosixPath,
    source_path: str,
    destination_path: str,
    formatter: BaseUpdateYML,
    yml_title: str,
    file_type: str,
):
    """
    Given
    - A yml file (integration, playbook or script) with no tests playbooks configured that are not configured
        in conf.json

    When
    - Entering 'N' into the prompt message that asks the user if he wants to configure those test playbooks into
        conf.json

    Then
    -  Ensure no exception is raised
    -  Ensure conf.json is not modified
    """

    # Setting up conf.json
    conf_json_path = tmp_path / "conf.json"
    mocker.patch(
        "demisto_sdk.commands.format.update_generic_yml.CONF_PATH", conf_json_path
    )

    with open(conf_json_path, "w") as file:
        json.dump(CONF_JSON_ORIGINAL_CONTENT, file, indent=4)

    saved_file_path = str(tmp_path / Path(destination_path).name)
    runner = CliRunner()
    # Running format in the first time
    result = runner.invoke(
        app, [FORMAT_CMD, "-i", source_path, "-o", saved_file_path, "-ngr"], input="N"
    )
    assert not result.exception
    assert "Skipping test playbooks configuration" in result.output
    with open(conf_json_path) as data_file:
        conf_json_content = json.load(data_file)
        assert conf_json_content == CONF_JSON_ORIGINAL_CONTENT


def _verify_conf_json_modified(
    test_playbooks: List, yml_title: str, conf_json_path: str
):
    """
    Verifying all test playbooks are configured in conf.json file
    """
    try:
        with open(conf_json_path) as data_file:
            conf_json_content = json.load(data_file)
            for test_playbook in test_playbooks:
                assert any(
                    test_config
                    for test_config in conf_json_content["tests"]
                    if is_test_config_match(
                        test_config,
                        test_playbook_id=test_playbook,
                        integration_id=yml_title,
                    )
                )
    except Exception:
        raise


def test_integration_format_remove_playbook_sourceplaybookid(
    mocker, tmp_path, monkeypatch
):
    """
    Given
    - Playbook with field  `sourceplaybookid`.
    - destination_path to write the formatted playbook to.

    When
    - Running the format command.
    - Entering '-at' so the prompt message about asking the user if he wants to add 'No tests' to the file will
        appear.

    Then
    - Ensure 'sourceplaybookid' was deleted from the yml file.
    """

    source_playbook_path = SOURCE_FORMAT_PLAYBOOK_COPY
    playbook_path = str(tmp_path / "format_new_playbook_copy.yml")
    runner = CliRunner()
    mocker.patch.object(BaseUpdate, "set_default_from_version", return_value=None)
    mocker.patch("builtins.input", return_value="y")
    with ChangeCWD(tmp_path):
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-i",
                source_playbook_path,
                "-o",
                playbook_path,
                "-at",
                "-ngr",
                "--console-log-threshold",
                "DEBUG",
            ],
            input="N",
        )
    # prompt = f'The file {source_playbook_path} has no test playbooks configured. Do you want to configure it with "No tests"'
    assert all(
        [
            current_str in result.output
            for current_str in [
                "======= Updating file ",
                f"Format Status on file: {source_playbook_path} - Success",
                f'Not formatting {source_playbook_path} with "No tests"',
            ]
        ]
    )
    with open(playbook_path) as f:
        yaml_content = yaml.load(f)
        assert "sourceplaybookid" not in yaml_content

    assert not result.exception


def test_format_on_valid_py(mocker, repo):
    """
    Given
    - A valid python file.

    When
    - Running format

    Then
    - Ensure format passes.
    """

    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    pack = repo.create_pack("PackName")
    integration = pack.create_integration("integration")
    valid_py = "test\n"
    integration.code.write(valid_py)

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-nv",
                "-i",
                integration.code.path,
                "--console-log-threshold",
                "DEBUG",
                "-ngr",
            ],
            catch_exceptions=True,
        )

    assert all(
        [
            current_str in result.output
            for current_str in [
                "======= Updating file",
                "Success",
                "Running autopep8 on file",
            ]
        ]
    )
    assert valid_py == integration.code.read()


def test_format_on_invalid_py_empty_lines(mocker, repo):
    """
    Given
    - Invalid python file - empty lines at the end of file.

    When
    - Running format

    Then
    - Ensure format passes.
    """

    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    pack = repo.create_pack("PackName")
    integration = pack.create_integration("integration")
    invalid_py = "test\n\n\n\n"
    integration.code.write(invalid_py)
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-nv",
                "-i",
                integration.code.path,
                "--console-log-threshold",
                "DEBUG",
                "-ngr",
            ],
            catch_exceptions=False,
        )

    assert all(
        [
            current_str in result.output
            for current_str in [
                "======= Updating file",
                "Success",
                "Running autopep8 on file",
            ]
        ]
    )
    assert invalid_py != integration.code.read()


def test_format_on_invalid_py_dict(mocker, repo):
    """
    Given
    - Invalid python file - missing spaces in dict.

    When
    - Running format

    Then
    - Ensure format passes.
    """

    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    pack = repo.create_pack("PackName")
    integration = pack.create_integration("integration")
    invalid_py = "{'test':'testing','test1':'testing1'}"
    integration.code.write(invalid_py)
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-nv",
                "-i",
                integration.code.path,
                "--console-log-threshold",
                "DEBUG",
                "-ngr",
            ],
            catch_exceptions=False,
        )

    assert all(
        [
            current_str in result.output
            for current_str in [
                "======= Updating file",
                "Success",
                "Running autopep8 on file",
            ]
        ]
    )
    assert invalid_py != integration.code.read()


def test_format_on_invalid_py_long_dict(mocker, repo, monkeypatch):
    """
    Given
    - Invalid python file - long dict.

    When
    - Running format

    Then
    - Ensure format passes.
    """

    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    pack = repo.create_pack("PackName")
    integration = pack.create_integration("integration")
    invalid_py = (
        "{'test':'testing','test1':'testing1','test2':'testing2','test3':'testing3',"
        "'test4':'testing4','test5':'testing5','test6':'testing6'}"
    )
    integration.code.write(invalid_py)
    with ChangeCWD(pack.repo_path):
        result = CliRunner(mix_stderr=False).invoke(
            app,
            [
                FORMAT_CMD,
                "-nv",
                "-i",
                integration.code.path,
                "--console-log-threshold",
                "DEBUG",
                "-ngr",
            ],
            catch_exceptions=False,
        )

    assert all(
        [
            current_str in result.output
            for current_str in [
                "======= Updating file",
                "Success",
            ]
        ]
    )
    assert "Running autopep8 on file" in result.output
    assert invalid_py != integration.code.read()


def test_format_on_invalid_py_long_dict_no_verbose(mocker, repo):
    """
    (This is the same test as the previous one only without verbose output)
    Given
    - Invalid python file - long dict.

    When
    - Running format

    Then
    - Ensure format passes and that the verbose is off
    """
    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    pack = repo.create_pack("PackName")
    integration = pack.create_integration("integration")
    invalid_py = (
        "{'test':'testing','test1':'testing1','test2':'testing2','test3':'testing3',"
        "'test4':'testing4','test5':'testing5','test6':'testing6'}"
    )
    integration.code.write(invalid_py)
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-nv",
                "-i",
                integration.code.path,
                "--console-log-threshold",
                "DEBUG",
                "-ngr",
            ],
            catch_exceptions=False,
        )

    assert all(
        [
            current_str in result.output
            for current_str in [
                "======= Updating file",
                "Success",
                "Running autopep8 on file",
            ]
        ]
    )
    assert invalid_py != integration.code.read()


def test_format_on_relative_path_playbook(mocker, repo, monkeypatch):
    """
    Given
    - playbook to validate on with a relative path

    When
    - Running format
    - Running validate

    Then
    - Ensure format passes.
    - Ensure validate passes.
    """

    pack = repo.create_pack("PackName")
    playbook = pack.create_playbook("playbook")
    playbook.create_default_playbook()
    mocker.patch.object(
        update_generic,
        "is_file_from_content_repo",
        return_value=(True, playbook.path),
    )
    mocker.patch.object(PlaybookValidator, "is_script_id_valid", return_value=True)
    mocker.patch.object(
        PlaybookValidator, "name_not_contain_the_type", return_value=True
    )
    mocker.patch.object(
        ContentEntityValidator, "validate_readme_exists", return_value=True
    )

    mocker.patch.object(tools, "is_external_repository", return_value=True)
    monkeypatch.setattr("builtins.input", lambda _: "N")
    with ChangeCWD(Path(playbook.path).parent):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [FORMAT_CMD, "-i", playbook.path, "-y", "-ngr"],
            catch_exceptions=False,
        )
        assert "======= Updating file" in result.output
        assert f"Format Status on file: {playbook.path} - Success" in result.output

        with ChangeCWD(repo.path):
            result = runner.invoke(
                app,
                [
                    "validate",
                    "-i",
                    "Packs/PackName/Playbooks/playbook.yml",
                    "--no-docker-checks",
                    "--no-conf-json",
                    "--allow-skipped",
                    "--run-old-validate",
                    "--skip-new-validate",
                ],
                catch_exceptions=False,
            )

    assert "The files are valid" in result.output


def test_format_integration_skipped_files(repo, mocker, monkeypatch):
    """
    Given:
        - Content pack with integration and doc files
        - Integration dir includes file artifacts from running lint (e.g. conftest.py)

    When:
        - Running format on the pack

    Then:
        - Ensure format runs successfully
        - Ensure format does not run files to be skipped
    """

    pack = repo.create_pack("PackName")
    pack.create_integration("integration")
    pack.create_doc_file()
    mocker.patch.object(ReadMeValidator, "is_docker_available", return_value=False)

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app, [FORMAT_CMD, "-i", str(pack.path), "-ngr"], catch_exceptions=False
    )

    assert all(
        [
            current_str in result.output
            for current_str in [
                "======= Updating file",
                "Success",
            ]
        ]
    )
    for excluded_file in excluded_files:
        assert excluded_file not in result.output


def test_format_commonserver_skipped_files(repo, mocker):
    """
    Given:
        - Base content pack with CommonServerPython script

    When:
        - Running format on the pack

    Then:
        - Ensure format runs successfully
        - Ensure format does not run files to be skipped
    """

    pack = repo.create_pack("Base")
    pack.create_script("CommonServerPython")
    mocker.patch.object(ReadMeValidator, "is_docker_available", return_value=False)

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [FORMAT_CMD, "-i", str(pack.path), "-ngr"],
        catch_exceptions=False,
    )

    assert all(
        [
            current_str in result.output
            for current_str in [
                "Success",
                "CommonServerPython.py",
            ]
        ]
    )

    commonserver_excluded_files = excluded_files[:]
    commonserver_excluded_files.remove("CommonServerPython.py")
    for excluded_file in commonserver_excluded_files:
        assert excluded_file not in result.output


def test_format_playbook_without_fromversion_no_preset_flag(repo, mocker, monkeypatch):
    """
    Given:
        - A playbook without fromversion

    When:
        - Running format on the pack with assume-yes flag without from-version flag

    Then:
        - Ensure format runs successfully
        - Ensure format adds fromversion with the oldest supported version to the playbook.
    """

    pack = repo.create_pack("Temp")
    playbook = pack.create_playbook("my_temp_playbook")
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    if "fromversion" in playbook_content:
        del playbook_content["fromversion"]

    assert "fromversion" not in playbook_content

    playbook.yml.write_dict(playbook_content)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [FORMAT_CMD, "-i", str(playbook.yml.path), "--assume-yes", "-ngr"],
    )
    assert "Success" in result.output
    assert playbook.yml.read_dict().get("fromversion") == "8.9.0"


def test_format_playbook_without_fromversion_with_preset_flag_silent(
    repo, mocker, monkeypatch
):
    """
    Given:
        - A playbook without fromversion

    When:
        - Running format on the pack with assume-yes flag with from-version flag

    Then:
        - Ensure format runs successfully
        - Ensure format adds fromversion with the given from-version.
        - Ensure playbook is converted to silent.
    """

    pack = repo.create_pack("Temp")
    playbook = pack.create_playbook("my_temp_playbook")
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    if "fromversion" in playbook_content:
        del playbook_content["fromversion"]

    assert "fromversion" not in playbook_content

    playbook.yml.write_dict(playbook_content)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [
            FORMAT_CMD,
            "-i",
            str(playbook.yml.path),
            "--assume-yes",
            "--from-version",
            "6.0.0",
            "-ngr",
        ],
    )
    assert "Success" in result.output
    assert "silent-" in playbook.yml.read_dict().get("name")
    assert "silent-" in playbook.yml.read_dict().get("id")
    assert playbook.yml.read_dict().get("issilent") is True
    assert playbook.yml.read_dict().get("fromversion") == "6.0.0"


def test_format_playbook_without_fromversion_with_preset_flag_manual_non_silent(
    repo, mocker, monkeypatch
):
    """
    Given:
        - A playbook without fromversion

    When:
        - Running format on the pack with from-version flag

    Then:
        - Ensure format runs successfully
        - Ensure format adds fromversion with the given from-version.
        - Ensure playbook is converted to non-silent.
    """

    pack = repo.create_pack("Temp")
    playbook = pack.create_playbook("my_temp_playbook")
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    if "fromversion" in playbook_content:
        del playbook_content["fromversion"]

    assert "fromversion" not in playbook_content

    playbook.yml.write_dict(playbook_content)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [FORMAT_CMD, "-i", str(playbook.yml.path), "--from-version", "6.0.0", "-ngr"],
        input="n",
    )
    assert "Success" in result.output
    assert "silent-" not in playbook.yml.read_dict().get("name")
    assert "silent-" not in playbook.yml.read_dict().get("id")
    assert playbook.yml.read_dict().get("issilent") is False
    assert playbook.yml.read_dict().get("fromversion") == "6.0.0"


def test_format_playbook_without_fromversion_without_preset_flag_manual(
    repo, mocker, monkeypatch
):
    """
    Given:
        - A playbook without fromversion

    When:
        - Running format on the pack

    Then:
        - Ensure format runs successfully
        - Ensure playbook is converted to silent.
    """

    pack = repo.create_pack("Temp")
    playbook = pack.create_playbook("my_temp_playbook")
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    if "fromversion" in playbook_content:
        del playbook_content["fromversion"]

    assert "fromversion" not in playbook_content

    playbook.yml.write_dict(playbook_content)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [FORMAT_CMD, "-i", str(playbook.yml.path), "-ngr"],
        input="y",
    )
    assert "Success" in result.output
    assert playbook.yml.read_dict().get("fromversion") == "8.9.0"
    assert "silent-" in playbook.yml.read_dict().get("name")
    assert playbook.yml.read_dict().get("issilent") is True


def test_format_playbook_copy_removed_from_name_and_id_silent(
    repo, mocker, monkeypatch
):
    """
    Given:
        - A playbook with name and id ending in `_copy`

    When:
        - Running format on the pack

    Then:
        - Ensure format runs successfully
        - Ensure format removes `_copy` from both name and id.
        - Ensure playbook is converted to silent.
    """

    pack = repo.create_pack("Temp")
    playbook = pack.create_playbook("my_temp_playbook")
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    playbook_id = playbook_content["id"]
    playbook_name = playbook_content["name"]
    playbook_content["id"] = playbook_id + "_copy"
    playbook_content["name"] = playbook_name + "_copy"

    playbook.yml.write_dict(playbook_content)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [FORMAT_CMD, "-i", str(playbook.yml.path), "-ngr"],
        input="y\n5.5.0",
    )
    assert "Success" in result.output
    assert playbook.yml.read_dict().get("fromversion") == "8.9.0"
    assert playbook.yml.read_dict().get("issilent") is True
    assert playbook.yml.read_dict().get("id") == f"silent-{playbook_id}"
    assert playbook.yml.read_dict().get("name") == f"silent-{playbook_name}"


def test_format_playbook_copy_removed_from_name_and_id_non_silent(
    repo, mocker, monkeypatch
):
    """
    Given:
        - A playbook with name and id ending in `_copy`

    When:
        - Running format on the pack

    Then:
        - Ensure format runs successfully
        - Ensure format removes `_copy` from both name and id.
        - Ensure playbook is converted to non-silent.
    """

    pack = repo.create_pack("Temp")
    playbook = pack.create_playbook("my_temp_playbook")
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    playbook_id = playbook_content["id"]
    playbook_name = playbook_content["name"]
    playbook_content["id"] = playbook_id + "_copy"
    playbook_content["name"] = playbook_name + "_copy"

    playbook.yml.write_dict(playbook_content)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [FORMAT_CMD, "-i", str(playbook.yml.path), "-ngr"],
        input="n\n5.5.0",
    )
    assert "Success" in result.output
    assert playbook.yml.read_dict().get("fromversion") == "6.10.0"
    assert playbook.yml.read_dict().get("issilent") is False
    assert playbook.yml.read_dict().get("id") == playbook_id
    assert playbook.yml.read_dict().get("name") == playbook_name


def test_format_playbook_no_input_specified_silent(mocker, repo, monkeypatch):
    """
    Given:
        - A playbook with name and id ending in `_copy`

    When:
        - Running format on the pack
        - The path of the playbook was not provided

    Then:
        - The command will find the changed playbook
        - Ensure format runs successfully
        - Ensure format removes `_copy` from both name and id.
        - Ensure playbook is converted to silent.
    """

    pack = repo.create_pack("Temp")
    playbook = pack.create_playbook("my_temp_playbook")
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    playbook_id = playbook_content["id"]
    playbook_name = playbook_content["name"]
    playbook_content["id"] = playbook_id + "_copy"
    playbook_content["name"] = playbook_name + "_copy"
    playbook.yml.write_dict(playbook_content)
    mocker.patch.object(
        format_module,
        "get_files_to_format_from_git",
        return_value=[str(playbook.yml.path)],
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [FORMAT_CMD, "-ngr"],
        input="y\n5.5.0",
    )
    assert "Success" in result.output
    assert playbook.yml.read_dict().get("id") == f"silent-{playbook_id}"
    assert playbook.yml.read_dict().get("name") == f"silent-{playbook_name}"
    assert playbook.yml.read_dict().get("fromversion") == "8.9.0"
    assert playbook.yml.read_dict().get("issilent") is True


def test_format_playbook_no_input_specified_non_silent(mocker, repo, monkeypatch):
    """
    Given:
        - A playbook with name and id ending in `_copy`

    When:
        - Running format on the pack
        - The path of the playbook was not provided

    Then:
        - The command will find the changed playbook
        - Ensure format runs successfully
        - Ensure format removes `_copy` from both name and id.
        - Ensure playbook is converted to non-silent.
    """

    pack = repo.create_pack("Temp")
    playbook = pack.create_playbook("my_temp_playbook")
    playbook.create_default_playbook()
    playbook_content = playbook.yml.read_dict()
    playbook_id = playbook_content["id"]
    playbook_name = playbook_content["name"]
    playbook_content["id"] = playbook_id + "_copy"
    playbook_content["name"] = playbook_name + "_copy"
    playbook.yml.write_dict(playbook_content)
    mocker.patch.object(
        format_module,
        "get_files_to_format_from_git",
        return_value=[str(playbook.yml.path)],
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [FORMAT_CMD, "-ngr"],
        input="n\n5.5.0",
    )
    assert "Success" in result.output
    assert playbook.yml.read_dict().get("id") == playbook_id
    assert playbook.yml.read_dict().get("name") == playbook_name
    assert playbook.yml.read_dict().get("fromversion") == "6.10.0"
    assert playbook.yml.read_dict().get("issilent") is False


def test_format_incident_type_layout_id(repo, mocker):
    """
    Given:
        - Content pack with incident type and layout
        - Layout with ID which is a UUID string
        - Incident type which is linked to the above layout

    When:
        - Running format on the content pack

    Then:
        - Verify layout ID is updated
        - Verify the updated layout ID is also updated in the incident type
    """

    mocker.patch.object(ReadMeValidator, "is_docker_available", return_value=False)

    pack = repo.create_pack("PackName")
    layout = pack.create_layoutcontainer(
        name="layout",
        content={
            "id": "8f503eb3-883d-4626-8a45-16f56995bd43",
            "name": "IncidentLayout",
            "group": "incident",
            "detailsV2": {"tabs": []},
        },
    )
    incident_type = pack.create_incident_type(
        name="incidentype",
        content={
            "layout": "8f503eb3-883d-4626-8a45-16f56995bd43",
            "color": "",
            "playbookId": "9f503eb3-333d-2226-7b45-16f56885bd45",
        },
    )
    playbook = pack.create_playbook(
        name="playbook",
        yml={
            "id": "9f503eb3-333d-2226-7b45-16f56885bd45",
            "name": "PlaybookName",
            "tasks": {},
            "fromversion": "5.0.0",
            "description": "",
        },
    )

    runner = CliRunner(mix_stderr=False)
    with ChangeCWD(repo.path):
        format_result = runner.invoke(
            app,
            [FORMAT_CMD, "-i", str(pack.path), "-y", "-ngr"],
            catch_exceptions=False,
        )

    assert format_result.exit_code == 0
    assert all(
        [
            current_str in format_result.output
            for current_str in [
                "Success",
                f"======= Updating file {pack.path}",
                f"======= Updating file {layout.path}",
                f"======= Updating file {incident_type.path}",
                f"======= Updating file {playbook.yml.path}",
            ]
        ]
    )

    with open(layout.path) as layout_file:
        layout_content = json.loads(layout_file.read())
        assert layout_content["name"] == layout_content["id"]

    with open(playbook.yml.path) as playbook_file:
        playbook_content = yaml.load(playbook_file)
        assert playbook_content["name"] == playbook_content["id"]

    with open(incident_type.path) as incident_type_file:
        incident_type_content = json.loads(incident_type_file.read())
        assert incident_type_content["layout"] == "IncidentLayout"
        assert incident_type_content["playbookId"] == "PlaybookName"


@pytest.mark.parametrize(
    "field_to_test, invalid_value, expected_value_after_format",
    [
        ("fromVersion", "6.0.0", "6.5.0"),
        ("group", 0, 4),
        ("id", "asset_operatingsystem", "generic_asset_operatingsystem"),
    ],
)
def test_format_generic_field_wrong_values(
    mocker, repo, field_to_test, invalid_value, expected_value_after_format
):
    """
    Given
    - Invalid generic field.

    When
    - Running format on it.

    Then
    - Ensure Format fixed the invalid value of the given generic field.
    - Ensure success message is printed.
    """

    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    mocker.patch(
        "demisto_sdk.commands.format.update_generic.GENERAL_DEFAULT_FROMVERSION",
        "6.5.0",
    )
    pack = repo.create_pack("PackName")
    generic_field = GENERIC_FIELD.copy()
    generic_field[field_to_test] = invalid_value
    pack.create_generic_field("generic-field", generic_field)
    generic_field_path = pack.generic_fields[0].path
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [FORMAT_CMD, "-i", generic_field_path, "-y", "-ngr"],
            catch_exceptions=False,
        )
        assert all(
            [
                current_str in result.output
                for current_str in [
                    "Setting fromVersion field",
                    f"======= Updating file {generic_field_path}",
                    "Success",
                ]
            ]
        )
        assert result.exit_code == 0

        # check that sdk format did change the wrong fromVersion to '6.5.0':
        with open(generic_field_path) as f:
            updated_generic_field = json.load(f)
        assert updated_generic_field[field_to_test] == expected_value_after_format


def test_format_generic_field_missing_from_version_key(mocker, repo):
    """
    Given
    - Invalid generic field  - fromVersion field is missing

    When
    - Running format on it.

    Then
    - Ensure Format fixed the given generic field - fromVersion field was added and it's value is 6.5.0
    - Ensure success message is printed.
    """

    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    mocker.patch(
        "demisto_sdk.commands.format.update_generic.GENERAL_DEFAULT_FROMVERSION",
        "6.5.0",
    )
    pack = repo.create_pack("PackName")
    generic_field = GENERIC_FIELD.copy()
    if generic_field["fromVersion"]:
        generic_field.pop("fromVersion")
    pack.create_generic_field("generic-field", generic_field)
    generic_field_path = pack.generic_fields[0].path
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [FORMAT_CMD, "-i", generic_field_path, "-y", "-ngr"],
            catch_exceptions=False,
        )
        assert all(
            [
                current_str in result.output
                for current_str in [
                    "Success",
                    f"======= Updating file {generic_field_path}",
                ]
            ]
        )
        assert result.exit_code == 0

        # check that sdk format did add a fromVersion key with '6.5.0' as a value:
        with open(generic_field_path) as f:
            updated_generic_field = json.load(f)
        assert updated_generic_field["fromVersion"] == GENERIC_FIELD["fromVersion"]


def test_format_generic_type_wrong_from_version(mocker, repo):
    """
    Given
    - Invalid generic type  - fromVersion field is below 6.5.0

    When
    - Running format on it.

    Then
    - Ensure Format fixed the invalid value of the given generic type.
    - Ensure success message is printed.
    """

    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    mocker.patch(
        "demisto_sdk.commands.format.update_generic.GENERAL_DEFAULT_FROMVERSION",
        "6.5.0",
    )

    pack = repo.create_pack("PackName")
    generic_type = GENERIC_TYPE.copy()
    generic_type["fromVersion"] = "6.0.0"
    pack.create_generic_type("generic-type", generic_type)
    generic_type_path = pack.generic_types[0].path
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [FORMAT_CMD, "-i", generic_type_path, "-y", "-ngr"],
            catch_exceptions=False,
        )
        assert all(
            [
                current_str in result.output
                for current_str in [
                    "Success",
                    f"======= Updating file {generic_type_path}",
                ]
            ]
        )
        assert result.exit_code == 0

        # check that sdk format did change the wrong fromVersion to '6.5.0':
        with open(generic_type_path) as f:
            updated_generic_type = json.load(f)
        assert updated_generic_type["fromVersion"] == GENERIC_TYPE["fromVersion"]


def test_format_generic_type_missing_from_version_key(mocker, repo):
    """
    Given
    - Invalid generic type  - fromVersion field is missing

    When
    - Running format on it.

    Then
    - Ensure Format fixed the given generic type - fromVersion field was added and it's value is 6.5.0
    - Ensure success message is printed.
    """

    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    mocker.patch(
        "demisto_sdk.commands.format.update_generic.GENERAL_DEFAULT_FROMVERSION",
        "6.2.0",
    )
    pack = repo.create_pack("PackName")
    generic_type = GENERIC_TYPE.copy()
    if generic_type["fromVersion"]:
        generic_type.pop("fromVersion")
    pack.create_generic_type("generic-type", generic_type)
    generic_type_path = pack.generic_types[0].path
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [FORMAT_CMD, "-i", generic_type_path, "-y", "-ngr"],
            catch_exceptions=False,
        )
        assert all(
            [
                current_str in result.output
                for current_str in [
                    "Success",
                    f"======= Updating file {generic_type_path}",
                ]
            ]
        )
        assert result.exit_code == 0

        # check that sdk format did add a fromVersion key with '6.5.0' as a value:
        with open(generic_type_path) as f:
            updated_generic_type = json.load(f)
        assert updated_generic_type["fromVersion"] == GENERIC_TYPE["fromVersion"]


def test_format_generic_module_wrong_from_version(mocker, repo):
    """
    Given
    - Invalid generic module  - fromVersion field is below 6.5.0

    When
    - Running format on it.

    Then
    - Ensure Format fixed the invalid value of the given generic module.
    - Ensure success message is printed.
    """

    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    mocker.patch(
        "demisto_sdk.commands.format.update_generic.GENERAL_DEFAULT_FROMVERSION",
        "6.2.0",
    )
    pack = repo.create_pack("PackName")
    generic_module = GENERIC_MODULE.copy()
    generic_module["fromVersion"] = "6.0.0"
    pack.create_generic_module("generic-module", generic_module)
    generic_module_path = pack.generic_modules[0].path
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [FORMAT_CMD, "-i", generic_module_path, "-y", "-ngr"],
            catch_exceptions=False,
        )
        assert all(
            [
                current_str in result.output
                for current_str in [
                    "Setting fromVersion field",
                    "Success",
                    f"======= Updating file {generic_module_path}",
                ]
            ]
        )
        assert result.exit_code == 0

        # check that sdk format did change the wrong fromVersion to '6.5.0':
        with open(generic_module_path) as f:
            updated_generic_module = json.load(f)
        assert updated_generic_module["fromVersion"] == GENERIC_MODULE["fromVersion"]


def test_format_generic_module_missing_from_version_key(mocker, repo):
    """
    Given
    - Invalid generic module  - fromVersion field is missing

    When
    - Running format on it.

    Then
    - Ensure Format fixed the given generic module - fromVersion field was added and it's value is 6.5.0
    - Ensure success message is printed.
    """

    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    mocker.patch(
        "demisto_sdk.commands.format.update_generic.GENERAL_DEFAULT_FROMVERSION",
        "6.2.0",
    )
    pack = repo.create_pack("PackName")
    generic_module = GENERIC_MODULE.copy()
    if generic_module["fromVersion"]:
        generic_module.pop("fromVersion")
    pack.create_generic_module("generic-module", generic_module)
    generic_module_path = pack.generic_modules[0].path
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [FORMAT_CMD, "-i", generic_module_path, "-y", "-ngr"],
            catch_exceptions=False,
        )
        assert all(
            [
                current_str in result.output
                for current_str in [
                    "Success",
                    f"======= Updating file {generic_module_path}",
                ]
            ]
        )
        assert result.exit_code == 0

        # check that sdk format did add a fromVersion key with '6.5.0' as a value:
        with open(generic_module_path) as f:
            updated_generic_module = json.load(f)
        assert updated_generic_module["fromVersion"] == GENERIC_MODULE["fromVersion"]


def test_format_generic_definition_wrong_from_version(mocker, repo):
    """
    Given
    - Invalid generic definition  - fromVersion field is below 6.5.0

    When
    - Running format on it.

    Then
    - Ensure Format fixed the invalid value of the given generic definition.
    - Ensure success message is printed.
    """

    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    mocker.patch(
        "demisto_sdk.commands.format.update_generic.GENERAL_DEFAULT_FROMVERSION",
        "6.2.0",
    )
    pack = repo.create_pack("PackName")
    generic_definition = GENERIC_DEFINITION.copy()
    generic_definition["fromVersion"] = "6.0.0"
    pack.create_generic_definition("generic-definition", generic_definition)
    generic_definition_path = pack.generic_definitions[0].path
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [FORMAT_CMD, "-i", generic_definition_path, "-y", "-ngr"],
            catch_exceptions=False,
        )
        assert all(
            [
                current_str in result.output
                for current_str in [
                    "Success",
                    f"======= Updating file {generic_definition_path}",
                ]
            ]
        )
        assert result.exit_code == 0

        # check that sdk format did change the wrong fromVersion to '6.5.0':
        with open(generic_definition_path) as f:
            updated_generic_definition = json.load(f)
        assert (
            updated_generic_definition["fromVersion"]
            == GENERIC_DEFINITION["fromVersion"]
        )


def test_format_generic_definition_missing_from_version_key(mocker, repo):
    """
    Given
    - Invalid generic definition  - fromVersion field is missing

    When
    - Running format on it.

    Then
    - Ensure Format fixed the given generic definition - fromVersion field was added and it's value is 6.5.0
    - Ensure success message is printed.
    """

    mocker.patch.object(
        update_generic, "is_file_from_content_repo", return_value=(False, "")
    )
    mocker.patch(
        "demisto_sdk.commands.format.update_generic.GENERAL_DEFAULT_FROMVERSION",
        "6.2.0",
    )
    pack = repo.create_pack("PackName")
    generic_definition = GENERIC_DEFINITION.copy()
    if generic_definition["fromVersion"]:
        generic_definition.pop("fromVersion")
    pack.create_generic_definition("generic-definition", generic_definition)
    generic_definition_path = pack.generic_definitions[0].path
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [FORMAT_CMD, "-i", generic_definition_path, "-y", "-ngr"],
            catch_exceptions=False,
        )
        assert all(
            [
                current_str in result.output
                for current_str in [
                    "Success",
                    f"======= Updating file {generic_definition_path}",
                ]
            ]
        )
        assert result.exit_code == 0

        # check that sdk format did add a fromVersion key with '6.5.0' as a value:
        with open(generic_definition_path) as f:
            updated_generic_definition = json.load(f)
        assert (
            updated_generic_definition["fromVersion"]
            == GENERIC_DEFINITION["fromVersion"]
        )


class TestFormatWithoutAddTestsFlag:
    def test_format_integrations_folder_with_add_tests(self, mocker, pack):
        """
        Given
        - An integration folder.

        When
        - Running format command on it

        Then
        -  Ensure no exception is raised.
        -  Ensure message asking to add tests is prompt.
        """

        runner = CliRunner()
        integration = pack.create_integration()
        integration.create_default_integration()
        integration.yml.update({"fromversion": "5.5.0"})
        integration_path = integration.yml.path
        mocker.patch.object(BaseUpdate, "set_default_from_version", return_value=None)
        mocker.patch.object(
            IntegrationValidator, "is_valid_category", return_value=True
        )

        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-i",
                integration_path,
                "-at",
                "-ngr",
                "--console-log-threshold",
                "DEBUG",
            ],
        )
        assert f'Not formatting {integration_path} with "No tests"' in result.output
        assert f'Formatting {integration_path} with "No tests"' not in result.output
        assert not result.exception

    def test_format_integrations_folder(self, mocker, pack):
        """
        Given
        - An integration folder.

        When
        - Running format command on it

        Then
        -  Ensure no exception is raised.
        -  Ensure 'No tests' is added to the yaml file.
        -  Ensure message asking to add tests is not prompt.
        -  Ensure a message for formatting automatically the yaml file is added.
        """

        runner = CliRunner()
        integration = pack.create_integration()
        integration.create_default_integration()
        integration_path = integration.yml.path
        mocker.patch.object(
            IntegrationValidator, "is_valid_category", return_value=True
        )
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-i",
                integration_path,
                "-ngr",
                "--console-log-threshold",
                "DEBUG",
            ],
            input="Y",
        )
        prompt = (
            f"The file {integration_path} has no test playbooks configured."
            f' Do you want to configure it with "No tests"?'
        )
        message = f'Formatting {integration_path} with "No tests"'
        assert not result.exception
        assert prompt not in result.output
        assert message in result.output

    def test_format_script_without_test_flag(self, mocker, monkeypatch, pack):
        """
        Given
        - An script folder.

        When
        - Running format command on it

        Then
        -  Ensure no exception is raised.
        -  Ensure 'No tests' is added to the yaml file.
        -  Ensure message asking to add tests is not prompt.
        -  Ensure a message for formatting automatically the yaml file is added.
        """

        runner = CliRunner()
        script = pack.create_script()
        script.create_default_script()
        script.yml.update({"fromversion": "5.5.0"})
        script_path = script.yml.path
        mocker.patch.object(BaseUpdate, "set_default_from_version", return_value=None)

        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-i",
                script_path,
                "-ngr",
                "--console-log-threshold",
                "DEBUG",
            ],
        )
        message = f'Formatting {script_path} with "No tests"'
        assert not result.exception
        assert message in result.output

    def test_format_playbooks_folder(self, mocker, monkeypatch, pack):
        """
        Given
        - A playbooks folder.

        When
        - Running format command on it

        Then
        -  Ensure no exception is raised.
        -  Ensure 'No tests' is added to the yaml file.
        -  Ensure message asking to add tests is not prompt.
        -  Ensure a message for formatting automatically the yaml file is added.
        """

        runner = CliRunner()
        playbook = pack.create_playbook()
        playbook.create_default_playbook()
        playbook.yml.update({"fromversion": "5.5.0"})
        playbooks_path = playbook.yml.path
        playbook.yml.delete_key("tests")
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-i",
                playbooks_path,
                "-ngr",
                "--console-log-threshold",
                "DEBUG",
            ],
            input="N",
        )
        message = f'Formatting {playbooks_path} with "No tests"'
        assert not result.exception
        assert message in result.output

        assert playbook.yml.read_dict().get("tests")[0] == "No tests (auto formatted)"

    def test_format_testplaybook_folder_without_add_tests_flag(self, pack):
        """
        Given
        - An TestPlaybook folder.

        When
        - Running format command on it

        Then
        -  Ensure no exception is raised.
        -  Ensure 'No tests' is NOT added to the yaml file.
        -  Ensure NO message for formatting automatically the yaml file is added.

        """
        runner = CliRunner()
        test_playbook = pack.create_test_playbook()
        test_playbook.create_default_test_playbook()
        test_playbook.yml.update({"fromversion": "5.5.0"})
        test_playbooks_path = test_playbook.yml.path
        test_playbook.yml.delete_key("tests")
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-i",
                test_playbooks_path,
                "-ngr",
                "--console-log-threshold",
                "DEBUG",
            ],
            input="N",
        )
        prompt = (
            f"The file {test_playbooks_path} has no test playbooks configured."
            f' Do you want to configure it with "No tests"?'
        )
        message = f'Formatting {test_playbooks_path} with "No tests"'
        assert not result.exception
        assert prompt not in result.output
        assert message not in result.output

        assert not test_playbook.yml.read_dict().get("tests")

    def test_format_test_playbook_folder_with_add_tests_flag(self, pack):
        """
        Given
        - An TestPlaybook folder.

        When
        - Running format command on it

        Then
        -  Ensure no exception is raised.
        -  Ensure 'No tests' is NOT added to the yaml file.
        -  Ensure NO message for formatting automatically the yaml file is added.

        """
        runner = CliRunner()
        test_playbook = pack.create_test_playbook()
        test_playbook.create_default_test_playbook()
        test_playbook.yml.update({"fromversion": "5.5.0"})
        test_playbooks_path = test_playbook.yml.path
        test_playbook.yml.delete_key("tests")
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-i",
                test_playbooks_path,
                "-at",
                "-ngr",
                "--console-log-threshold",
                "DEBUG",
            ],
            input="N",
        )
        prompt = (
            f"The file {test_playbooks_path} has no test playbooks configured."
            f' Do you want to configure it with "No tests"?'
        )
        message = f'Formatting {test_playbooks_path} with "No tests"'
        assert not result.exception
        assert prompt not in result.output
        assert message not in result.output

        assert not test_playbook.yml.read_dict().get("tests")

    def test_format_layouts_folder_without_add_tests_flag(
        self, mocker, monkeypatch, repo
    ):
        """
        Given
        - An Layouts folder.

        When
        - Running format command on it

        Then
        -  Ensure no exception is raised.
        -  Ensure 'No tests' is NOT added to the yaml file.
        -  Ensure NO message for formatting automatically the yaml file is added.
        """

        runner = CliRunner()
        pack = repo.create_pack("PackName")
        layout = pack.create_layoutcontainer(
            name="layout",
            content={
                "id": "8f503eb3-883d-4626-8a45-16f56995bd43",
                "name": "IncidentLayout",
                "group": "incident",
                "detailsV2": {"tabs": []},
            },
        )
        layouts_path = layout.path
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-i",
                layouts_path,
                "-y",
                "-ngr",
                "--console-log-threshold",
                "DEBUG",
            ],
        )
        message = f'Formatting {layouts_path} with "No tests"'
        message1 = f"Format Status on file: {layouts_path} - Success"

        assert not result.exception
        assert message not in result.output
        assert message1 in result.output

    def test_format_layouts_folder_with_add_tests_flag(self, mocker, monkeypatch, repo):
        """
        Given
        - An Layouts folder.

        When
        - Running format command on it

        Then
        -  Ensure no exception is raised.
        -  Ensure 'No tests' is NOT added to the yaml file.
        -  Ensure NO message for formatting automatically the yaml file is added.
        """

        runner = CliRunner()
        pack = repo.create_pack("PackName")
        layout = pack.create_layoutcontainer(
            name="layout",
            content={
                "id": "8f503eb3-883d-4626-8a45-16f56995bd43",
                "name": "IncidentLayout",
                "group": "incident",
                "detailsV2": {"tabs": []},
            },
        )
        layouts_path = layout.path
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-i",
                layouts_path,
                "-at",
                "-y",
                "-ngr",
                "--console-log-threshold",
                "DEBUG",
            ],
        )
        assert not result.exception
        assert f'Formatting {layouts_path} with "No tests"' not in result.output
        assert f"Format Status on file: {layouts_path} - Success" in result.output


def test_verify_deletion_from_conf_pack_format_with_deprecate_flag(
    mocker, monkeypatch, repo
):
    """
    Given
    - A pack with an integration and a TPB defined in the yml.

    When
    - Executing format with -d flag.

    Then
    -  Ensure deletion from test.conf
    """

    # Prepare mockers

    # Prepare content
    # Create pack with integration and with test playbook in the yml.
    pack = repo.create_pack("TestPack")
    integration = pack.create_integration("TestIntegration")
    integration.yml.update({"tests": ["test_playbook"]})
    pack_path = pack.path
    repo_path = repo.path
    # We don't need to format empty readme files
    Path(f"{repo_path}/Packs/TestPack/Integrations/TestIntegration/README.md").unlink(
        missing_ok=True
    )

    Path(f"{repo_path}/Packs/TestPack/README.md").unlink(missing_ok=True)

    # Prepare conf
    test_conf_data = {
        "tests": [
            {"integrations": ["TestIntegration"], "playbookID": "New Integration Test"},
            {"integrations": ["TestIntegration"], "playbookID": "test_playbook"},
            {
                "integrations": ["AnotherTestIntegration"],
                "playbookID": "another_test_playbook",
            },
        ]
    }
    conf_json_path = f"{repo_path}/Tests/conf.json"
    with open(conf_json_path, "w") as file:
        json.dump(test_conf_data, file, indent=4)

    # Run
    with ChangeCWD(repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app,
            [
                FORMAT_CMD,
                "-i",
                f"{pack_path}",
                "-d",
                "-ngr",
                "--console-log-threshold",
                "DEBUG",
            ],
            input="\n",
        )

    # Asserts
    assert not result.exception
    conf_content = get_dict_from_file(conf_json_path)[0]
    assert conf_content.get("tests") == [
        {
            "integrations": ["AnotherTestIntegration"],
            "playbookID": "another_test_playbook",
        }
    ]


def test_verify_deletion_from_conf_script_format_with_deprecate_flag(
    mocker, monkeypatch, repo
):
    """
    Given
    - A pack with a script and a TPB defined in the yml.

    When
    - Executing format with -d flag.

    Then
    -  Ensure deletion from test.conf
    """

    # Prepare mockers

    # Prepare content
    # Create pack with script and with test playbook in the yml.
    pack = repo.create_pack("TestPack")
    script = pack.create_script("TestScript")
    script.yml.update({"tests": ["test_playbook_for_script"]})
    script_path = script.path
    repo_path = repo.path

    # We don't need to format empty readme files
    Path(f"{repo_path}/Packs/TestPack/Scripts/TestScript/README.md").unlink(
        missing_ok=True
    )
    Path(f"{repo_path}/Packs/TestPack/README.md").unlink(missing_ok=True)

    # Prepare conf
    test_conf_data = {
        "tests": [
            {"integrations": ["TestIntegration"], "playbookID": "New Integration Test"},
            {"scripts": ["TestScript"], "playbookID": "test_playbook_for_script"},
            {
                "scripts": ["TestScript", "AnotherTestScript"],
                "playbookID": "test_playbook_for_script",
            },
        ]
    }
    conf_json_path = f"{repo_path}/Tests/conf.json"
    with open(conf_json_path, "w") as file:
        json.dump(test_conf_data, file, indent=4)

    # Run
    with ChangeCWD(repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            app, [FORMAT_CMD, "-i", f"{script_path}", "-d", "-ngr"], input="\n"
        )

    # Asserts
    assert not result.exception
    conf_content = get_dict_from_file(conf_json_path)[0]
    assert conf_content.get("tests") == [
        {"integrations": ["TestIntegration"], "playbookID": "New Integration Test"},
        {"scripts": ["AnotherTestScript"], "playbookID": "test_playbook_for_script"},
    ]


def test_format_incident_field_with_no_graph(mocker, monkeypatch, repo):
    """
    Given
    - An incident field.

    When
    - Running format command on it with the flag -ngr.

    Then
    -  Ensure that the marketplacev2 wasn't removed from the incident field marketplaces list.
    """

    runner = CliRunner()
    pack = repo.create_pack("PackName")
    incident_field = pack.create_incident_field(
        name="incident_field",
        content={
            "cliName": "incidentfield",
            "id": "incident_incidentfield",
            "name": "Incident Field",
            "Aliases": [
                {
                    "cliName": "aliasincidentfield",
                    "type": "shortText",
                    "name": "Alias Incident Field",
                }
            ],
            "marketplaces": ["marketplacev2"],
        },
    )
    alias_incident_field_content = {
        "cliName": "aliasincidentfield",
        "id": "incident_aliasincidentfield",
        "name": "Alias Incident Field",
        "marketplaces": ["marketplacev2", "xsoar"],
    }
    alias_incident_field = pack.create_incident_field(
        name="alias_incident_field", content=alias_incident_field_content
    )

    result = runner.invoke(
        app, [FORMAT_CMD, "-i", incident_field.path, "-at", "-y", "-ngr"]
    )
    message = (
        f"Skipping formatting of marketplaces field of aliases for {incident_field.path}"
        f" as the no-graph argument was given."
    )
    assert result.exit_code == 0
    assert not result.exception
    assert message in result.output

    # get_dict_from_file returns a tuple of 2 object. The first is the content of the file,
    # the second is the type of the file.
    file_content = get_dict_from_file(alias_incident_field.path)[0]
    assert file_content.get("marketplaces", []) == ["marketplacev2", "xsoar"]


def test_format_mapper_with_ngr_flag(mocker, monkeypatch, repo):
    """
    Given
    - A mapper.

    When
    - Running format command on it with the flag -ngr (no graph)

    Then
    -  Ensure that the unknown field wasn't removed from the mapper.
    """

    incident_field_name = "Unknown Incident Field"
    mapper_content = {
        "description": "",
        "feed": False,
        "id": "Mapper - Incoming Mapper",
        "mapping": {
            "Mapper Finding": {
                "dontMapEventToLabels": True,
                "internalMapping": {incident_field_name: {"simple": "Item"}},
            },
        },
        "name": "Mapper - Incoming Mapper",
        "type": "mapping-incoming",
        "version": -1,
        "fromVersion": GENERAL_DEFAULT_FROMVERSION,
    }

    runner = CliRunner()
    pack = repo.create_pack("PackName")
    mapper = pack.create_mapper(name="mapper", content=mapper_content)

    result = runner.invoke(app, [FORMAT_CMD, "-i", mapper.path, "-at", "-y", "-ngr"])
    message = f"Skipping formatting of non-existent-fields for {mapper.path} as the no-graph argument was given."
    assert result.exit_code == 0
    assert not result.exception
    assert message in result.output

    # get_dict_from_file returns a tuple of 2 object. The first is the content of the file,
    # the second is the type of the file.
    file_content = get_dict_from_file(mapper.path)[0]
    expected_internal_mapping = {incident_field_name: {"simple": "Item"}}
    assert (
        file_content.get("mapping", {}).get("Mapper Finding", {}).get("internalMapping")
        == expected_internal_mapping
    )


def test_format_on_layout_no_graph_flag(mocker, monkeypatch, repo):
    """
    Given
    - A layout.

    When
    - Running format command on it, with the flag -ngr (no graph)

    Then
    -  Ensure that the unknown field wasn't removed from the layout.
    """

    incident_field_object_id = "unknown-incident-field"
    layout_content = {
        "detailsV2": {
            "tabs": [
                {
                    "id": "caseinfoid",
                    "name": "Incident Info",
                    "sections": [
                        {
                            "displayType": "ROW",
                            "h": 2,
                            "i": "caseinfoid-fce71720-98b0-11e9-97d7-ed26ef9e46c8",
                            "isVisible": True,
                            "items": [
                                {
                                    "endCol": 2,
                                    "fieldId": incident_field_object_id,
                                    "height": 22,
                                    "id": "id1",
                                    "index": 0,
                                    "sectionItemType": "field",
                                    "startCol": 0,
                                },
                                {
                                    "endCol": 2,
                                    "fieldId": "known-incident-field",
                                    "height": 22,
                                    "id": "id2",
                                    "index": 0,
                                    "sectionItemType": "field",
                                    "startCol": 0,
                                },
                            ],
                        }
                    ],
                }
            ]
        },
        "group": "incident",
        "id": "Layout",
        "name": "Layout",
        "system": False,
        "version": -1,
        "fromVersion": GENERAL_DEFAULT_FROMVERSION,
        "description": "",
        "marketplaces": ["xsoar"],
    }

    runner = CliRunner()
    pack = repo.create_pack("PackName")
    layout = pack.create_layoutcontainer(name="Layout", content=layout_content)

    result = runner.invoke(
        app, [FORMAT_CMD, "-i", layout.path, "-at", "-y", "-ngr"]
    )  # run format without the graph
    message = f"Skipping formatting of non-existent-fields for {layout.path} as the no-graph argument was given."
    assert result.exit_code == 0
    assert not result.exception
    assert message in result.output

    # get_dict_from_file returns a tuple of 2 object. The first is the content of the file,
    # the second is the type of the file.
    file_content = get_dict_from_file(layout.path)[0]
    assert file_content == layout_content
