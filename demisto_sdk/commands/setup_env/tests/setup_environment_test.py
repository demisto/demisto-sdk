from pathlib import Path

import dotenv
import pytest

import demisto_sdk.commands.content_graph.objects.content_item as content_item
import demisto_sdk.commands.setup_env.setup_environment as setup_environment
from demisto_sdk.commands.content_graph.parsers.pack import PackParser
from demisto_sdk.commands.setup_env.setup_environment import (
    docker_helper,
    json,
    json5,
    setup_env,
)


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
    setup_env([integration.yml.path], create_virtualenv=create_virtualenv)
    dotenv_text = (repo_path / ".env").read_text()
    assert "PYTHONPATH" in dotenv_text
    assert "MYPYPATH" in dotenv_text
    assert "CommonServerPython" in dotenv_text

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
