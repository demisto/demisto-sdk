import os
import re
import shutil
import subprocess
import venv
from enum import Enum
from pathlib import Path
from typing import Tuple

import dotenv
import google
from google.cloud import secretmanager

from demisto_sdk.commands.common import docker_helper
from demisto_sdk.commands.common.constants import DEF_DOCKER
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.handlers.json.json5_handler import JSON5_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack

json5 = JSON5_Handler()
json = JSON_Handler()


class IDE(Enum):
    VSCODE = "vscode"
    PYCHARM = "pycharm"


IDE_TO_FOLDER = {IDE.VSCODE: ".vscode", IDE.PYCHARM: ".idea"}


def get_integration_params(project_id: str, secret_id: str):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

    # Access the secret version.
    try:
        response = client.access_secret_version(name=name)
    except google.api_core.exceptions.NotFound:
        logger.warning("The secret is not found in the secret manager")
        return {}
    except google.api_core.exceptions.PermissionDenied:
        logger.warning(
            "Insufficient permissions for gcloud. If you have the correct permissions, run `gcloud auth application-default login`"
        )
        return {}
    # Return the decoded payload.
    payload = response.payload.data.decode("UTF-8")
    return json5.loads(payload).get("params")


def copy_demistomock(integration_script: IntegrationScript):
    if integration_script.type == "powershell":
        (integration_script.path.parent / "demistomock.ps1").unlink(missing_ok=True)
        shutil.copy(
            CONTENT_PATH / "Tests" / "demistomock" / "demistomock.ps1",
            integration_script.path.parent / "demistomock.ps1",
        )
    else:
        (integration_script.path.parent / "demistomock.py").unlink(missing_ok=True)
        shutil.copy(
            CONTENT_PATH / "Tests" / "demistomock" / "demistomock.py",
            integration_script.path.parent / "demistomock.py",
        )


def add_init_file_in_test_data(integration_script: IntegrationScript):
    if (integration_script.path.parent / "test_data").exists():
        (integration_script.path.parent / "test_data" / "__init__.py").touch()


def configure_dotenv():
    dotenv_path = CONTENT_PATH / ".env"
    env_vars = dotenv.dotenv_values(dotenv_path)
    env_vars["PYTHONPATH"] = ":".join([str(path) for path in PYTHONPATH])
    env_vars["MYPYPATH"] = ":".join([str(path) for path in PYTHONPATH])
    for key, value in env_vars.items():
        dotenv.set_key(dotenv_path, key, value)


def configure_settings(
    ide_folder: Path, integration_script: IntegrationScript, interpreter_path: Path
):
    shutil.copy(Path(__file__).parent / "settings.json", ide_folder / "settings.json")
    with open(ide_folder / "settings.json") as f:
        settings = json5.load(f)

    settings["python.defaultInterpreterPath"] = str(interpreter_path)
    settings["python.testing.cwd"] = str(integration_script.path.parent)
    with open(ide_folder / "settings.json", "w") as f:
        json.dump(settings, f, indent=4)


def configure_vscode(
    ide_folder: Path,
    integration_script: IntegrationScript,
    test_docker_image: str,
    interpreter_path: Path,
):
    demisto_params = CONTENT_PATH / "params.json"
    configure_settings(ide_folder, integration_script, interpreter_path)
    launch_json_path = ide_folder / "launch.json"
    tasks_json_path = ide_folder / "tasks.json"
    launch_json: dict = {}
    tasks_json: dict = {}
    if integration_script.type == "powershell":
        shutil.copyfile(Path(__file__).parent / "launch-powershell.json", launch_json_path)
        with open(launch_json_path) as f:
            launch_json_template = json5.load(f)
        tasks_json_template = {}
        script_path = integration_script.path.with_suffix(".ps1")
        launch_json = {
            "configurations": [
                {
                    "script": str(script_path),
                    "cwd": str(CONTENT_PATH)
                }
            ]
        }
    elif integration_script.type.startswith("python"):
        shutil.copyfile(Path(__file__).parent / "tasks.json", tasks_json_path)
        shutil.copyfile(Path(__file__).parent / "launch-python.json", launch_json_path)
        with open(launch_json_path) as f:
            launch_json_template = json5.load(f)
        with open(tasks_json_path) as f:
            tasks_json_template = json5.load(f)
        script_path = integration_script.path.with_suffix(".py")
        test_script_path = integration_script.path.parent / f"{integration_script.path.stem}_test.py"
        launch_json = {
            "configurations": [
                {
                    "name": f"Docker: Debug ({integration_script.path.stem})",
                    "python": {
                        "pathMappings": [{"localRoot": str(CONTENT_PATH), "remoteRoot": "/app"}]
                    }
                },
                {
                    "name": f"Docker: Debug tests ({integration_script.path.stem})",
                    "python": {
                        "pathMappings": [{"localRoot": str(CONTENT_PATH), "remoteRoot": "/app"}]
                    }
                },
                {
                    "name": f"Python: Debug locally ({integration_script.path.stem})",
                    "program": str(script_path),
                    "cwd": str(CONTENT_PATH),
                    "env": {"DEMISTO_PARAMS": str(demisto_params)}
                }
            ]
        }
        tasks_json = {
            "tasks": [
                {
                    "python": {
                        "file": f"/app/{str(script_path.relative_to(CONTENT_PATH))}"
                    },
                    "dockerRun": {
                        "image": integration_script.docker_image,
                        "env": {"DEMISTO_PARAMS": f"/app/{demisto_params.relative_to(CONTENT_PATH)}"},
                        "volumes": [{"localPath": str(CONTENT_PATH), "containerPath": "/app"}]
                    }
                },
                {
                    "python": {
                        "args": [
                            "-s",
                            f"/app/{test_script_path.relative_to(CONTENT_PATH)}",
                            "-vv"
                        ]
                    },
                    "dockerRun": {
                        "image": test_docker_image,
                        "customOptions": f"-w /app/{script_path.relative_to(CONTENT_PATH)}",
                        "env": {"PYTHONPATH": ":".join([f"/app/{python_path.relative_to(CONTENT_PATH)}" for python_path in PYTHONPATH])},
                        "volumes": [{"localPath": str(CONTENT_PATH), "containerPath": "/app"}]
                    }
                }
            ]
        }
    launch_json = launch_json_template.update(launch_json)
    tasks_json = tasks_json_template.update(tasks_json)
    with open(launch_json_path, "w") as f:
        json.dump(launch_json, f, indent=4)
    with open(tasks_json_path, "w") as f:
        json.dump(tasks_json, f, indent=4)

def setup(
    file_paths: Tuple[Path, ...],
    ide: IDE = IDE.VSCODE,
    create_virtualenv: bool = False,
    overwrite_virtualenv: bool = False,
):
    ide_folder = CONTENT_PATH / IDE_TO_FOLDER[ide]
    docker_client = docker_helper.init_global_docker_client()
    for file_path in file_paths:
        integration_script = BaseContent.from_path(Path(file_path))
        assert isinstance(
            integration_script, IntegrationScript
        ), "Expected Integration Script"
        copy_demistomock(integration_script)
        add_init_file_in_test_data(integration_script)
        configure_dotenv()
        docker_image = integration_script.docker_image
        interpreter_path = CONTENT_PATH / ".venv" / "bin" / "python"
        # replace " ", "(", ")" with "_"
        secret_id = re.sub(r'[ ()]', '_', integration_script.name)
        if project_id := os.getenv("GCP_PROJECT_ID"):
            params = get_integration_params(project_id, secret_id)
            with open(ide_folder / "params.json", "w") as f:
                json.dump(params, f, indent=4)

        if not docker_image:
            docker_image = DEF_DOCKER
        (
            test_docker_image,
            errors,
        ) = docker_helper.get_docker().pull_or_create_test_image(
            docker_image, integration_script.type
        )
        if errors:
            raise RuntimeError(f"Failed to pull/create test docker image for {docker_image}: {errors}")

        if create_virtualenv and integration_script.type.startswith("python"):
            pack = integration_script.in_pack
            assert isinstance(pack, Pack), "Expected pack"
            ide_folder = pack.path / IDE_TO_FOLDER[ide]
            requirements = (
                docker_client.containers.run(
                    test_docker_image, command="pip list --format=freeze", remove=True
                )
                .decode()
                .split("\n")
            )
            venv_path = integration_script.path.parent / "venv"
            interpreter_path = venv_path / "bin" / "python"
            if venv_path.exists() and not overwrite_virtualenv:
                continue
            logger.info(f"Creating virtualenv for {integration_script.name}")
            shutil.rmtree(venv_path, ignore_errors=True)
            venv.create(venv_path, with_pip=True)
            for req in requirements:
                try:
                    if not req:
                        continue
                    subprocess.run(
                        [
                            f"{venv_path / 'bin' / 'pip'}",
                            "-q",
                            "--disable-pip-version-check",
                            "install",
                            req,
                        ],
                        check=True,
                    )
                    logger.info(f"Installed {req}")
                except subprocess.CalledProcessError:
                    logger.warning(f"Could not install {req}, skipping...")

        if ide == IDE.VSCODE:
            configure_vscode(
                ide_folder, integration_script, test_docker_image, interpreter_path
            )

