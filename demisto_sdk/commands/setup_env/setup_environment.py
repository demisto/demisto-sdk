import os
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
from demisto_sdk.commands.common.handlers.json.json5_handler import JSON5_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack

json = JSON5_Handler()


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
    return json.loads(payload).get("params")


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
        settings = json.load(f)

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
    demisto_params = ide_folder / "params.json"
    configure_settings(ide_folder, integration_script, interpreter_path)
    launch_json_path = ide_folder / "launch.json"
    tasks_json_path = ide_folder / "tasks.json"
    launch_json = {}
    tasks_json = {}
    if integration_script.type == "powershell":
        shutil.copyfile(
            Path(__file__).parent / "launch-powershell.json", ide_folder / "launch.json"
        )
        script_path = integration_script.path.with_suffix(".ps1")

        with open(launch_json_path) as f:
            launch_json = json.load(f)

        launch_json["configurations"][0]["script"] = str(script_path)
        launch_json["configurations"][0]["cwd"] = str(CONTENT_PATH)

    if integration_script.type.startswith("python"):
        shutil.copyfile(Path(__file__).parent / "tasks.json", ide_folder / "tasks.json")
        shutil.copyfile(
            Path(__file__).parent / "launch-python.json", ide_folder / "launch.json"
        )
        script_path = integration_script.path.with_suffix(".py")
        test_script_path = (
            integration_script.path.parent / f"{integration_script.path.stem}_test.py"
        )
        tag = f"{integration_script.name}-pytest"
        with open(ide_folder / "launch.json") as f:
            launch_json = json.load(f)
        with open(ide_folder / "tasks.json") as f:
            tasks_json = json.load(f)
        launch_json["configurations"][0][
            "name"
        ] = f"Docker: Debug ({integration_script.name})"
        launch_json["configurations"][1][
            "name"
        ] = f"Docker: Debug tests ({integration_script.name})"
        launch_json["configurations"][2][
            "name"
        ] = f"Python: Debug locally ({integration_script.name})"
        launch_json["configurations"][2]["program"] = str(script_path)
        launch_json["configurations"][2]["cwd"] = str(CONTENT_PATH)
        launch_json["configurations"][2]["env"]["DEMISTO_PARAMS"] = str(demisto_params)

        tasks_json["tasks"][0]["dockerBuild"]["buildArgs"][
            "IMAGENAME"
        ] = test_docker_image
        tasks_json["tasks"][0]["dockerBuild"]["tag"] = tag

        tasks_json["tasks"][1]["python"]["file"] = str(
            f"/app/{str(script_path.relative_to(CONTENT_PATH))}"
        )
        tasks_json["tasks"][1]["dockerRun"]["image"] = integration_script.docker_image
        tasks_json["tasks"][1]["dockerRun"]["env"]["DEMISTO_PARAMS"] = f"/app/{demisto_params.relative_to(CONTENT_PATH)}"
        
        docker_python_path = [f"/app/{python_path.relative_to(CONTENT_PATH)}" for python_path in PYTHONPATH]
        tasks_json["tasks"][1]["dockerRun"]["env"]["PYTHONPATH"] = ":".join(docker_python_path)
        tasks_json["tasks"][2]["python"]["args"] = [
            "-s",
            f"/app/{test_script_path.relative_to(CONTENT_PATH)}",
            "-vv",
        ]
        tasks_json["tasks"][2]["dockerRun"]["image"] = test_docker_image
        tasks_json["tasks"][2]["dockerRun"]["tag"] = tag
        tasks_json["tasks"][2]["dockerRun"][
            "customOptions"
        ] = f"-w /app/{script_path.relative_to(CONTENT_PATH)}"
        tasks_json["tasks"][2]["dockerRun"]["env"]["PYTHONPATH"] = ":".join(docker_python_path)
    with open(launch_json_path, "w") as f:
        json.dump(launch_json, f, quote_keys=True, indent=4)
    with open(tasks_json_path, "w") as f:
        json.dump(tasks_json, f, quote_keys=True, indent=4)


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
        if create_virtualenv and integration_script.type.startswith("python"):
            pack = integration_script.in_pack
            assert isinstance(pack, Pack), "Expected pack"
            ide_folder = pack.path / IDE_TO_FOLDER[ide]
            requirements = (
                docker_client.containers.run(
                    docker_image, command="pip list --format=freeze", remove=True
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
        secret_id = integration_script.object_id.replace(" ", "_")
        if project_id := os.getenv("GCP_PROJECT_ID"):
            params = get_integration_params(project_id, secret_id)
            with open(ide_folder / "params.json", "w") as f:
                json.dump(params, f, quote_keys=True, trailing_commas=False, indent=4)

        if not docker_image:
            docker_image = DEF_DOCKER
        (
            test_docker_image,
            errors,
        ) = docker_helper.get_docker().pull_or_create_test_image(
            docker_image, integration_script.type
        )
        if errors:
            raise Exception(f"Failed to pull/create docker image: {errors}")
        if ide == IDE.VSCODE:
            configure_vscode(
                ide_folder, integration_script, test_docker_image, interpreter_path
            )
