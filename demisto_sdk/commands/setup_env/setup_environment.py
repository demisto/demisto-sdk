import os
import re
import shutil
import subprocess
import venv
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple
from demisto_sdk.commands.setup_env.test_integration import create_integration_instance
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
from demisto_sdk.commands.content_graph.objects.integration import Integration
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
    except Exception:
        logger.warning(
            f"Failed to get secret {secret_id} from secret manager, skipping"
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
        if not value:
            continue
        dotenv.set_key(dotenv_path, key, value)


def configure_vscode_settings(
    ide_folder: Path, integration_script: IntegrationScript, interpreter_path: Path
):
    shutil.copy(Path(__file__).parent / "settings.json", ide_folder / "settings.json")
    with open(ide_folder / "settings.json") as f:
        settings = json5.load(f)

    settings["python.defaultInterpreterPath"] = str(interpreter_path)
    settings["python.testing.cwd"] = str(integration_script.path.parent)
    with open(ide_folder / "settings.json", "w") as f:
        json.dump(settings, f, indent=4)


def configure_vscode_tasks(
    ide_folder: Path, integration_script: IntegrationScript, test_docker_image: str
):
    if integration_script.type == "powershell":
        logger.debug("Powershell integration, skipping tasks.json")
        return
    docker_python_path = [
        f"/app/{path.relative_to(CONTENT_PATH)}"
        for path in PYTHONPATH
        if "demisto_sdk" not in str(path)
    ]
    tasks = {
        "version": "2.0.0",
        "tasks": [
            {
                "type": "docker-run",
                "label": "docker-run: debug",
                "python": {
                    "file": f"/app/{integration_script.path.with_suffix('.py').relative_to(CONTENT_PATH)}"
                },
                "dockerRun": {
                    "image": integration_script.docker_image,
                    "volumes": [
                        {"localPath": str(CONTENT_PATH), "containerPath": "/app"}
                    ],
                    "env": {
                        "DEMISTO_PARAMS": "/app/.vscode/params.json",
                        "PYTHONPATH": ":".join(docker_python_path),
                    },
                },
            },
            {
                "type": "docker-run",
                "label": "docker-run: test",
                "dependsOn": ["docker-build"],
                "python": {
                    "module": "pytest",
                    "args": [
                        "-s",
                        "-vv",
                        f"/app/{integration_script.path.with_name(integration_script.path.stem + '_test.py').relative_to(CONTENT_PATH)}",
                    ],
                },
                "dockerRun": {
                    "image": test_docker_image,
                    "volumes": [
                        {
                            "localPath": str(CONTENT_PATH),
                            "containerPath": "/app",
                        }
                    ],
                    "customOptions": f"-w /app/{integration_script.path.parent.relative_to(CONTENT_PATH)}",
                    "env": {"PYTHONPATH": ":".join(docker_python_path)},
                },
            },
        ],
    }
    with open(ide_folder / "tasks.json", "w") as f:
        json.dump(tasks, f, indent=4)


def configure_vscode_launch(ide_folder: Path, integration_script: IntegrationScript):
    if integration_script.type == "powershell":
        launch = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "PowerShell: Debug Integration",
                    "type": "PowerShell",
                    "request": "launch",
                    "script": str(integration_script.path.with_suffix(".ps1")),
                    "cwd": "${workspaceFolder}",
                }
            ],
        }
    else:
        launch = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": f"Docker: Debug ({integration_script.path.stem})",
                    "type": "docker",
                    "request": "launch",
                    "preLaunchTask": "docker-run: debug",
                    "python": {
                        "pathMappings": [
                            {"localRoot": str(CONTENT_PATH), "remoteRoot": "/app"}
                        ],
                        "projectType": "general",
                        "justMyCode": False,
                    },
                },
                {
                    "name": f"Docker: Debug tests ({integration_script.path.stem})",
                    "type": "docker",
                    "request": "launch",
                    "preLaunchTask": "docker-run: test",
                    "python": {
                        "pathMappings": [
                            {
                                "localRoot": str(CONTENT_PATH),
                                "remoteRoot": "/app",
                            },
                        ],
                        "projectType": "general",
                        "justMyCode": False,
                    },
                },
                {
                    "name": "Python: Debug Integration locally",
                    "type": "python",
                    "request": "launch",
                    "program": str(integration_script.path.with_suffix(".py")),
                    "console": "integratedTerminal",
                    "cwd": "${workspaceFolder}",
                    "justMyCode": False,
                },
                {
                    "name": "Python: Debug Tests",
                    "type": "python",
                    "request": "launch",
                    "program": "${file}",
                    "purpose": ["debug-test"],
                    "console": "integratedTerminal",
                    "justMyCode": False,
                },
            ],
        }
        with open(ide_folder / "launch.json", "w") as f:
            json.dump(launch, f, indent=4)


def configure_vscode(
    ide_folder: Path,
    integration_script: IntegrationScript,
    test_docker_image: str,
    interpreter_path: Path,
):
    configure_vscode_settings(ide_folder, integration_script, interpreter_path)
    configure_vscode_tasks(ide_folder, integration_script, test_docker_image)
    configure_vscode_launch(ide_folder, integration_script)


def setup(
    file_paths: Tuple[Path, ...],
    ide: IDE = IDE.VSCODE,
    create_virtualenv: bool = False,
    overwrite_virtualenv: bool = False,
    secret_id: Optional[str] = None,
    instance_name: Optional[str] = None,
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
        secret_id = secret_id or re.sub(r"[ ()]", "_", integration_script.name)
        if (project_id := os.getenv("DEMISTO_GCP_PROJECT_ID")) and isinstance(integration_script, Integration):
            params = get_integration_params(project_id, secret_id)
            if params and instance_name:
                if (instance_created := create_integration_instance(
                    integration_script.name,
                    instance_name,
                    params,
                    params.get("byoi", True),
                )) and instance_created[0]:
                    logger.info(f"Created integration instance {instance_created[0]['name']}")
                else:
                    logger.warning(f"Failed to create integration instance {instance_name}")
            with open(CONTENT_PATH / ".vscode" / "params.json", "w") as f:
                json.dump(params, f, indent=4)
        else:
            logger.info("Skipping searching in Google Secret Manager as DEMISTO_GCP_PROJECT_ID is not set")
        if not docker_image:
            docker_image = DEF_DOCKER
        (
            test_docker_image,
            errors,
        ) = docker_helper.get_docker().pull_or_create_test_image(
            docker_image, integration_script.type
        )
        if errors:
            raise RuntimeError(
                f"Failed to pull/create test docker image for {docker_image}: {errors}"
            )

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
