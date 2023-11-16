import contextlib
import os
import re
import shutil
import subprocess
import tempfile
import venv
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import dotenv
from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common import docker_helper
from demisto_sdk.commands.common.clients import (
    get_client_from_server_type,
)
from demisto_sdk.commands.common.constants import DEF_DOCKER
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.handlers import DEFAULT_JSON5_HANDLER as json5
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    SecretManagerException,
    get_integration_params,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack

DOTENV_PATH = CONTENT_PATH / ".env"


class IDE(Enum):
    VSCODE = "vscode"
    PYCHARM = "pycharm"


IDE_TO_FOLDER = {IDE.VSCODE: ".vscode", IDE.PYCHARM: ".idea"}


def add_init_file_in_test_data(integration_script: IntegrationScript):
    if (test_data_dir := (integration_script.path.parent / "test_data")).exists():
        (test_data_dir / "__init__.py").touch()


def configure_vscode_settings(
    ide_folder: Path,
    integration_script: Optional[IntegrationScript] = None,
    interpreter_path: Optional[Path] = None,
    devcontainer: bool = False,
):
    shutil.copy(Path(__file__).parent / "settings.json", ide_folder / "settings.json")
    with open(ide_folder / "settings.json") as f:
        settings = json5.load(f)
    if devcontainer:
        interpreter_path = Path("/usr/local/bin/python")
    if interpreter_path:
        settings["python.defaultInterpreterPath"] = str(interpreter_path)
    if integration_script:
        if devcontainer:
            testing_path = f"workspaces/content/{integration_script.path.parent.relative_to(CONTENT_PATH)}"
        else:
            testing_path = str(integration_script.path.parent)
        settings["python.testing.cwd"] = testing_path
    if devcontainer:
        python_path = get_docker_python_path("/workspaces/content")
    else:
        python_path = [str(path) for path in PYTHONPATH if str(path)]

    settings["python.analysis.extraPaths"] = python_path
    with open(ide_folder / "settings.json", "w") as f:
        json5.dump(settings, f, indent=4)


def get_docker_python_path(docker_prefix: str) -> List[str]:
    docker_python_path = []
    for path in PYTHONPATH:
        with contextlib.suppress(ValueError):
            # we can't add paths which is not relative to CONTENT_PATH, and `is_relative_to is not working on python3.8`
            docker_python_path.append(
                f"{docker_prefix}/{path.relative_to(CONTENT_PATH.absolute())}"
            )
    if (
        f"{docker_prefix}/Packs/Base/Scripts/CommonServerPython"
        not in docker_python_path
    ):
        raise RuntimeError(
            "Could not set debug-in-docker on VSCode. Probably CONTENT_PATH is not set properly."
        )
    return docker_python_path


def update_dotenv(values: Dict[str, str], quote_mode="always"):
    env_vars = dotenv.dotenv_values(DOTENV_PATH)
    env_vars.update(values)
    for key, value in env_vars.items():
        if value:
            dotenv.set_key(DOTENV_PATH, key, value, quote_mode=quote_mode)
        else:
            logger.warning(f"empty value for {key}, not setting it")


def configure_dotenv():
    """
    This functions configures the .env file located with PYTHONPATH and MYPYPATH
    This is needed for discovery and linting for CommonServerPython, demistomock and API Modules files.
    """
    DOTENV_PATH.touch()
    python_path_values = ":".join((str(path) for path in PYTHONPATH))
    update_dotenv({"PYTHONPATH": python_path_values, "MYPYPATH": python_path_values})


def configure_vscode_tasks(
    ide_folder: Path, integration_script: IntegrationScript, test_docker_image: str
):
    if integration_script.type == "powershell":
        logger.debug("Powershell integration, skipping tasks.json")
        return
    docker_python_path = get_docker_python_path("/app")

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
                            "PYTHONPATH": ":".join(docker_python_path),
                        },
                        "envFiles": [str(DOTENV_PATH)],
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
        json5.dump(build_tasks(), f, indent=4)


def configure_vscode_launch(
    ide_folder: Path, integration_script: IntegrationScript, devcontainer: bool = False
):
    def build_launch():
        if integration_script.type == "powershell":
            launch = {
                "version": "0.2.0",
                "configurations": [
                    {
                        "name": "PowerShell: Debug Integration",
                        "type": "PowerShell",
                        "request": "launch",
                        "script": f"/workspaces/content/{integration_script.path.relative_to(CONTENT_PATH)}"
                        if devcontainer
                        else str(integration_script.path.with_suffix(".ps1")),
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
                        "program": f"/workspaces/content/{integration_script.path.relative_to(CONTENT_PATH)}"
                        if devcontainer
                        else str(integration_script.path.with_suffix(".py")),
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
            if devcontainer:
                # keep only the last
                launch["configurations"] = launch["configurations"][2:]

        return launch

    with open(ide_folder / "launch.json", "w") as f:
        json5.dump(build_launch(), f, indent=4)


def configure_devcontainer(
    integration_script: IntegrationScript, test_docker_image: str
):
    """This function configures the `.devcontainer` files to allow opening the integration inside a devcontainer

    Args:
        integration_script (IntegrationScript): The integration/script to configure.
        test_docker_image (str): The test image of the integration/script.
    """
    devcontainer_template_folder = Path(__file__).parent / ".devcontainer"
    with open(devcontainer_template_folder / "devcontainer.json") as f:
        devcontainer_json = json5.load(f)
    devcontainer_path = integration_script.path.parent / ".devcontainer"
    shutil.rmtree(devcontainer_path, ignore_errors=True)
    shutil.copytree(devcontainer_template_folder, devcontainer_path, dirs_exist_ok=True)

    docker_python_path = get_docker_python_path("/workspaces/content")
    devcontainer_json["build"]["args"]["IMAGENAME"] = test_docker_image
    devcontainer_json["remoteEnv"]["PYTHONPATH"] = ":".join(docker_python_path)
    devcontainer_json["remoteEnv"]["MYPYPATH"] = ":".join(docker_python_path)
    configure_vscode_launch(devcontainer_path, integration_script, devcontainer=True)
    configure_vscode_settings(devcontainer_path, integration_script, devcontainer=True)
    with open(devcontainer_path / "devcontainer.json", "w") as f:
        json5.dump(devcontainer_json, f, indent=4)


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
    configure_devcontainer(integration_script, test_docker_image)


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
            params = get_integration_params(secret_id, project_id)
            if params and instance_name:
                try:
                    upload_and_create_instance(
                        integration_script, instance_name, params, test_module
                    )
                except ApiException as e:
                    logger.warning(
                        f"Failed to create integration instance {instance_name}. Error {e}"
                    )
            update_dotenv({"DEMISTO_PARAMS": json.dumps(params)}, quote_mode="never")
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
    with tempfile.TemporaryDirectory() as temp_dir:
        pack.upload(
            client=client.client,
            marketplace=client.marketplace,
            target_demisto_version=client.version,
            zip=True,
            destination_zip_dir=Path(temp_dir),
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


def add_demistomock_and_commonserveruser(integration_script: IntegrationScript):
    shutil.copy(
        CONTENT_PATH / "Tests" / "demistomock" / "demistomock.py",
        integration_script.path.parent / "demistomock.py",
    )
    (integration_script.path.parent / "CommonServerUserPython.py").touch()


def configure_integration(
    ide: IDE,
    file_path: Path,
    create_virtualenv: bool,
    overwrite_virtualenv: bool,
    secret_id: Optional[str],
    instance_name: Optional[str],
    test_module: bool,
):
    """Configures the environment of the integration

    Args:
        ide (IDE): The IDE to configure to
        file_path (Path): The filepath of the integration
        create_virtualenv (bool): Whether create a virtual environment
        overwrite_virtualenv (bool): Whether overwrite the virtual environment
        secret_id (Optional[str]): The secret id to use
        instance_name (Optional[str]): The instance name to configure on XSOAR/XSIAM. If None, will not configure.
        test_module (bool): Whether run test module on the instance on XSOAR/XSIAM

    Raises:
        RuntimeError: If configuring failed (for instance, Docker is turned off)
    """
    ide_folder = CONTENT_PATH / IDE_TO_FOLDER[ide]
    integration_script = BaseContent.from_path(Path(file_path))
    assert isinstance(
        integration_script, IntegrationScript
    ), "Expected Integration Script"
    add_demistomock_and_commonserveruser(integration_script)
    add_init_file_in_test_data(integration_script)
    docker_image = integration_script.docker_image
    interpreter_path = CONTENT_PATH / ".venv" / "bin" / "python"
    configure_params(integration_script, secret_id, instance_name, test_module)
    if not docker_image:
        docker_image = DEF_DOCKER
    try:
        docker_helper.init_global_docker_client()
    except docker_helper.DockerException:
        logger.error(
            "Failed to initialize docker client. Make sure Docker is running and configured correctly"
        )
        raise
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
        (pack.path / ".env").symlink_to(DOTENV_PATH)
        if create_virtualenv and integration_script.type.startswith("python"):
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
    configure_dotenv()
    if not file_paths:
        (CONTENT_PATH / "CommonServerUserPython.py").touch()
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
