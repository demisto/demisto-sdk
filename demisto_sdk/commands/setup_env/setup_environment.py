import contextlib
import os
import re
import shutil
import subprocess
import venv
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

import dotenv
from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common import docker_helper
from demisto_sdk.commands.common.clients import (
    get_client_from_server_type,
)
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
from demisto_sdk.utils.utils import SecretManagerException, get_integration_params

json5 = JSON5_Handler()
json = JSON_Handler()


class IDE(Enum):
    VSCODE = "vscode"
    PYCHARM = "pycharm"


IDE_TO_FOLDER = {IDE.VSCODE: ".vscode", IDE.PYCHARM: ".idea"}


def add_init_file_in_test_data(integration_script: IntegrationScript):
    if (test_data_dir := (integration_script.path.parent / "test_data")).exists():
        (test_data_dir / "__init__.py").touch()


def configure_dotenv():
    """
    This functions configures the .env file located with PYTHONPATH and MYPYPATH
    This is needed for discovery and liniting for CommonServerPython, demistomock and API Modules files.
    """
    dotenv_path = CONTENT_PATH / ".env"
    env_vars = dotenv.dotenv_values(dotenv_path)
    python_path_values = ":".join((str(path) for path in PYTHONPATH))
    env_vars["PYTHONPATH"] = python_path_values
    env_vars["MYPYPATH"] = python_path_values
    for key, value in env_vars.items():
        if value:
            dotenv.set_key(dotenv_path, key, value)
        else:
            logger.warning(f"empty value for {key}, not setting it")


def configure_vscode_settings(
    ide_folder: Path,
    integration_script: Optional[IntegrationScript] = None,
    interpreter_path: Optional[Path] = None,
):
    shutil.copy(Path(__file__).parent / "settings.json", ide_folder / "settings.json")
    with open(ide_folder / "settings.json") as f:
        settings = json5.load(f)
    if interpreter_path:
        settings["python.defaultInterpreterPath"] = str(interpreter_path)
    if integration_script:
        settings["python.testing.cwd"] = str(integration_script.path.parent)
    settings["python.analysis.extraPaths"] = [
        str(path) for path in PYTHONPATH if str(path)
    ]
    with open(ide_folder / "settings.json", "w") as f:
        json.dump(settings, f, indent=4)


def configure_vscode_tasks(
    ide_folder: Path, integration_script: IntegrationScript, test_docker_image: str
):
    if integration_script.type == "powershell":
        logger.debug("Powershell integration, skipping tasks.json")
        return
    docker_python_path = []
    for path in PYTHONPATH:
        with contextlib.suppress(ValueError):
            # we can't add paths which is not relative to CONTENT_PATH, and `is_relative_to is not working on python3.8`
            docker_python_path.append(
                f"/app/{path.relative_to(CONTENT_PATH.absolute())}"
            )

    def build_tasks():
        return {
            "version": "2.0.0",
            "tasks": [
                {
                    "type": "docker-run",
                    "label": "docker-run: debug",
                    "python": {
                        "file": f"/app/{integration_script.path.with_suffix('.py').relative_to(CONTENT_PATH.absolute())}"
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
                            f"/app/{integration_script.path.with_name(integration_script.path.stem + '_test.py').relative_to(CONTENT_PATH.absolute())}",
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
                        "customOptions": f"-w /app/{integration_script.path.parent.relative_to(CONTENT_PATH.absolute())}",
                        "env": {"PYTHONPATH": ":".join(docker_python_path)},
                    },
                },
            ],
        }

    with open(ide_folder / "tasks.json", "w") as f:
        json.dump(build_tasks(), f, indent=4)


def configure_vscode_launch(ide_folder: Path, integration_script: IntegrationScript):
    def build_launch():
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
            return launch
        with open(ide_folder / "launch.json", "w") as f:
            json.dump(build_launch(), f, indent=4)


def configure_vscode(
    ide_folder: Path,
    integration_script: IntegrationScript,
    test_docker_image: str,
    interpreter_path: Path,
):
    """This functions configures VSCode for the integration script

    Args:
        ide_folder (Path): The ".vscode" folder to configure
        integration_script (IntegrationScript): The integration script to configure
        test_docker_image (str): The test docker image to use for running tests
        interpreter_path (Path): The local interpreter path to configure
    """
    ide_folder.mkdir(exist_ok=True)
    configure_vscode_settings(ide_folder, integration_script, interpreter_path)
    configure_vscode_tasks(ide_folder, integration_script, test_docker_image)
    configure_vscode_launch(ide_folder, integration_script)


def install_virtualenv(
    integration_script: IntegrationScript,
    test_docker_image: str,
    overwrite_virtualenv: bool,
) -> Path:
    """This function installs a virtualenv for the integration script using the test docker image

    Args:
        integration_script (IntegrationScript): The integration script object
        test_docker_image (str): The test docker image
        overwrite_virtualenv (bool): Whether to overwrite existing virtualenv

    Returns:
        Path: The created virtualenv path
    """
    docker_client = docker_helper.init_global_docker_client()
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
        logger.info(f"Using existing virtualenv in {venv_path}")
        return interpreter_path
    logger.info(f"Creating virtualenv for {integration_script.name}")
    shutil.rmtree(venv_path, ignore_errors=True)
    venv.create(venv_path, with_pip=True)
    for req in requirements:
        if not req:
            continue
        try:
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
    return interpreter_path


def configure_params(
    integration_script: IntegrationScript,
    secret_id: Optional[str],
    instance_name: Optional[str],
    test_module: bool,
) -> None:
    """Configuring the integration parameters locally and in XSOAR/XSIAM

    Args:
        integration_script (IntegrationScript): The integration script object configure params to
        secret_id (Optional[str]): The secret id of the parameters. defaults to the inegration name.
        instance_name (Optional[str]): The instance name to configure on XSOAR/XSIAM. If None, will not configure.
        test_module (bool): Whether test-module will run or not.
    """

    if not secret_id:
        secret_id = integration_script.name.replace(" ", "_")
        secret_id = re.sub(r"[()]", "", secret_id)
    if (project_id := os.getenv("DEMISTO_SDK_GCP_PROJECT_ID")) and isinstance(
        integration_script, Integration
    ):
        try:
            params = get_integration_params(project_id, secret_id)
            if params and instance_name:
                try:
                    upload_and_create_instance(
                        integration_script, instance_name, params, test_module
                    )
                except ApiException as e:
                    logger.warning(
                        f"Failed to create integration instance {instance_name}. Error {e}"
                    )
            (CONTENT_PATH / ".vscode").mkdir(exist_ok=True)
            with open(CONTENT_PATH / ".vscode" / "params.json", "w") as f:
                json.dump(params, f, indent=4)
        except SecretManagerException:
            logger.warning(
                f"Failed to fetch integration params from Google Secret Manager for {secret_id}"
            )

    else:
        logger.info(
            "Skipping searching in Google Secret Manager as DEMISTO_SDK_GCP_PROJECT_ID is not set"
        )


def upload_and_create_instance(
    integration_script: Integration, instance_name: str, params: dict, test_module: bool
):
    client = get_client_from_server_type()
    pack = integration_script.in_pack
    assert isinstance(pack, Pack)
    pack.upload(
        client=client.client,
        marketplace=client.marketplace,
        target_demisto_version=client.version,
        zip=True,
    )
    logger.info(f"Uploaded pack {pack.name} to {client.base_url}")
    client.create_integration_instance(
        integration_script.object_id,
        instance_name,
        params,
        is_long_running=integration_script.long_running,
        should_test=test_module,
    )
    logger.info(f"Created integration instance for {integration_script.object_id}")


def configure_integration(
    ide: IDE,
    file_path: Path,
    create_virtualenv: bool,
    overwrite_virtualenv: bool,
    secret_id: Optional[str],
    instance_name: Optional[str],
    test_module: bool,
):
    ide_folder = CONTENT_PATH / IDE_TO_FOLDER[ide]
    integration_script = BaseContent.from_path(Path(file_path))
    assert isinstance(
        integration_script, IntegrationScript
    ), "Expected Integration Script"
    add_init_file_in_test_data(integration_script)
    configure_dotenv()
    docker_image = integration_script.docker_image
    interpreter_path = CONTENT_PATH / ".venv" / "bin" / "python"
    configure_params(integration_script, secret_id, instance_name, test_module)
    if not docker_image:
        docker_image = DEF_DOCKER
    (test_docker_image, errors,) = docker_helper.get_docker().pull_or_create_test_image(
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
        interpreter_path = install_virtualenv(
            integration_script, test_docker_image, overwrite_virtualenv
        )

    if ide == IDE.VSCODE:
        configure_vscode(
            ide_folder, integration_script, test_docker_image, interpreter_path
        )


def setup_env(
    file_paths: Tuple[Path, ...],
    ide: IDE = IDE.VSCODE,
    create_virtualenv: bool = False,
    overwrite_virtualenv: bool = False,
    secret_id: Optional[str] = None,
    instance_name: Optional[str] = None,
    test_module: bool = False,
) -> None:
    """This function sets up the development environment for integration scripts

    Args:
        file_paths (Tuple[Path, ...]): File paths to set integration
        ide (IDE, optional): The IDE to setup the environment for. Defaults to IDE.VSCODE.
        create_virtualenv (bool, optional): Whether create virtual environment or not. Defaults to False.
        overwrite_virtualenv (bool, optional): Whether overwrite the existing virtual environment. Defaults to False.
        secret_id (Optional[str], optional): The secret id try to fetch from Google Secret Manager. Defaults to the integration name. Defaults to None.
        instance_name (Optional[str], optional): The instance name to configure on XSOAR/XSIAM. Defaults to None.

    Raises:
        RuntimeError:
    """
    if not file_paths:
        configure_dotenv()
        ide_folder = CONTENT_PATH / IDE_TO_FOLDER[ide]
        if ide == IDE.VSCODE:
            ide_folder.mkdir(exist_ok=True)
            configure_vscode_settings(ide_folder)
    for file_path in file_paths:
        configure_integration(
            ide,
            file_path,
            create_virtualenv,
            overwrite_virtualenv,
            secret_id,
            instance_name,
            test_module,
        )
