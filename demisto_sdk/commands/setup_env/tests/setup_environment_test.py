from pathlib import Path

import dotenv
import pytest
from lxml import etree

import demisto_sdk.commands.content_graph.objects.content_item as content_item
import demisto_sdk.commands.setup_env.setup_environment as setup_environment
from demisto_sdk.commands.content_graph.parsers.pack import PackParser
from demisto_sdk.commands.setup_env.setup_environment import (
    IDEType,
    docker_helper,
    json,
    json5,
    setup_env,
)

TESTS_DATA_DIR = Path(__file__).parent / "tests_data"


@pytest.mark.parametrize("create_virtualenv", [False, True])
def test_setup_env_vscode(mocker, monkeypatch, pack, create_virtualenv):
    """
    Given:
        - pack fixture with integration

    When:
        - Calling setup environment of the integration

    Then:
        - The environment is setup correctly in VSCode
    """
    monkeypatch.setenv("DEMISTO_SDK_GCP_PROJECT_ID", 3)
    image = "python3"
    test_image = "test/python3-sha"
    params = {"username": "user", "password": "pass"}
    repo_path = Path(pack.repo_path)
    mocker.patch.object(setup_environment, "CONTENT_PATH", repo_path)
    mocker.patch.object(setup_environment, "DOTENV_PATH", repo_path / ".env")

    mocker.patch.object(
        setup_environment,
        "PYTHONPATH",
        [repo_path / "Packs/Base/Scripts/CommonServerPython"],
    )

    mocker.patch.object(setup_environment, "add_demistomock_and_commonserveruser")

    mocker.patch.object(content_item, "CONTENT_PATH", repo_path)
    mocker.patch.object(
        docker_helper.DockerBase,
        "get_or_create_test_image",
        return_value=(test_image, ""),
    )
    mocker.patch.object(
        setup_environment, "get_integration_params", return_value=params
    )

    integration = pack.create_integration(docker_image=image)
    if create_virtualenv:
        interpreter_path = Path(integration.path) / "venv" / "bin" / "python"
        mocker.patch.object(
            setup_environment,
            "install_virtualenv",
            return_value=Path(integration.path) / "venv" / "bin" / "python",
        )
        mocker.patch.object(PackParser, "parse_ignored_errors", return_value={})
    else:
        interpreter_path = repo_path / ".venv" / "bin" / "python"
    setup_env(
        file_paths=(integration.yml.path,),
        ide_type=IDEType.VSCODE,
        create_virtualenv=create_virtualenv,
    )
    dotenv_text = (repo_path / ".env").read_text()
    assert "DEMISTO_PARAMS" in dotenv_text
    assert "PYTHONPATH" not in dotenv_text
    vscode_folder = (
        repo_path / ".vscode" if not create_virtualenv else Path(pack.path) / ".vscode"
    )
    with open(vscode_folder / "launch.json") as f:
        launch_json = json5.load(f)
    with open(vscode_folder / "tasks.json") as f:
        tasks_json = json5.load(f)
    with open(vscode_folder / "settings.json") as f:
        settings_json = json5.load(f)

    launch_json_configs = launch_json["configurations"]
    assert len(launch_json_configs) == 4
    assert launch_json_configs[0]["name"] == "Docker: Debug (integration_0)"
    assert launch_json_configs[0]["type"] == "docker"

    assert launch_json_configs[1]["name"] == "Docker: Debug tests (integration_0)"
    assert launch_json_configs[1]["type"] == "docker"

    tasks = tasks_json["tasks"]
    assert (
        tasks[0]["python"]["file"]
        == "/app/Packs/pack_0/Integrations/integration_0/integration_0.py"
    )
    assert tasks[0]["dockerRun"]["image"] == image
    assert tasks[1]["python"]["module"] == "pytest"
    assert (
        tasks[1]["python"]["args"][-1]
        == "/app/Packs/pack_0/Integrations/integration_0/integration_0_test.py"
    )
    assert tasks[1]["dockerRun"]["image"] == test_image

    assert json.loads(dotenv.get_key(repo_path / ".env", "DEMISTO_PARAMS")) == params

    assert settings_json["python.defaultInterpreterPath"] == str(interpreter_path)


@pytest.mark.parametrize(
    "sample_file, expected_updated_sample_file, expected_added_entries",
    [
        (
            TESTS_DATA_DIR / "idea_configuration" / "samples" / "sample1.iml",
            TESTS_DATA_DIR
            / "idea_configuration"
            / "expected_updated_files"
            / "sample1.iml",
            1,
        ),
        (
            TESTS_DATA_DIR / "idea_configuration" / "samples" / "sample2.iml",
            TESTS_DATA_DIR
            / "idea_configuration"
            / "expected_updated_files"
            / "sample2.iml",
            2,
        ),
    ],
)
def test_update_pycharm_config_xml_data(
    sample_file: Path, expected_updated_sample_file: Path, expected_added_entries: int
):
    """
    Given:
        - A sample file with a configuration that needs to be updated

    When:
        - Calling update_pycharm_config_xml_data

    Then:
        - The configuration is updated correctly
    """
    assert sample_file.exists()
    assert expected_updated_sample_file.exists()

    python_discovery_paths = [Path("test0/test1"), Path("test2/test3")]

    sample_file_content = etree.parse(str(sample_file))
    expected_updated_sample_file_content = expected_updated_sample_file.read_text()

    added_entries = setup_environment.update_pycharm_config_xml_data(
        config_data=sample_file_content,
        python_discovery_paths=python_discovery_paths,
    )

    assert added_entries == expected_added_entries

    sample_file_content_str = etree.tostring(
        sample_file_content, pretty_print=True, xml_declaration=True, encoding="utf-8"
    ).decode("utf-8")

    assert sample_file_content_str == expected_updated_sample_file_content
