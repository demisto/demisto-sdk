from pathlib import Path

import pytest

import demisto_sdk.commands.content_graph.objects.content_item as content_item
import demisto_sdk.commands.setup_env.setup_environment as setup_environment
from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.setup_env.setup_environment import docker_helper, setup_env


@pytest.mark.parametrize("create_virtualenv", [False, True])
def test_setup_env_vscode(mocker, pack, create_virtualenv):
    image = "python3"
    test_image = "test/python3-sha"
    params = {"username": "user", "password": "pass"}
    repo_path = Path(pack.repo_path)
    mocker.patch.object(setup_environment, "CONTENT_PATH", repo_path)
    mocker.patch.object(content_item, "CONTENT_PATH", repo_path)
    mocker.patch.object(
        docker_helper.DockerBase,
        "pull_or_create_test_image",
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
    launch_json = get_file(vscode_folder / "launch.json")
    tasks_json = get_file(vscode_folder / "tasks.json")
    params_json = get_file(repo_path / ".vscode" / "params.json")
    settings_json = get_file(vscode_folder / "settings.json")
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

    assert params_json == params

    assert settings_json["python.defaultInterpreterPath"] == str(interpreter_path)
