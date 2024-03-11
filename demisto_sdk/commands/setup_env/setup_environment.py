import contextlib
import os
import re
import shutil
import subprocess
import tempfile
import venv
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import dotenv
from demisto_client.demisto_api.rest import ApiException
from lxml import etree

from demisto_sdk.commands.common import docker_helper
from demisto_sdk.commands.common.clients import (
    get_client_from_server_type,
)
from demisto_sdk.commands.common.constants import DEF_DOCKER
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.docker.docker_image import DockerImage
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

BACKUP_FILES_SUFFIX = ".demisto_sdk_backup"
DOTENV_PATH = CONTENT_PATH / ".env"


class IDEType(Enum):
    PYCHARM = "PyCharm"
    VSCODE = "VSCode"


IDE_TO_FOLDER = {IDEType.VSCODE: ".vscode", IDEType.PYCHARM: ".idea"}


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

    settings["python.analysis.extraPaths"] = [
        path for path in python_path if "site-packages" not in path
    ]
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


def update_dotenv(
    file_path: Path, values: Dict[str, Optional[str]], quote_mode="never"
):
    """
    Configure the .env file with the given values. Generates the file if it doesn't exist.

    Args:
        file_path (Path): The path to the .env file
        values (Dict[str, str]): The values to set
        quote_mode (str): The quote mode to use. Defaults to "never"
    """
    file_path.touch(exist_ok=True)
    env_vars = dotenv.dotenv_values(file_path)
    env_vars.update(values)
    for key, value in env_vars.items():
        if value:
            dotenv.set_key(DOTENV_PATH, key, value, quote_mode=quote_mode)
        else:
            logger.warning(f"Empty value for '{key}'. Skipping...")


def update_pycharm_config_file(file_path: Path, python_discovery_paths: List[Path]):
    """
    Configure and update the .iml file to add the given python paths to the module discovery.

    Args:
        file_path (Path): The path to the .iml file to update
        python_discovery_paths (List[Path]): The python paths to add to the module discovery
    """
    if not file_path.exists():
        logger.warning(
            f"Could not find file '{file_path}'.\n"
            "This can happen if the project has not been opened in the IDE yet.\n"
            "Module discovery will not be configured."
        )
        return

    config_data = etree.parse(str(file_path))
    added_entries_count = update_pycharm_config_xml_data(
        config_data=config_data, python_discovery_paths=python_discovery_paths
    )

    if (
        added_entries_count > 0
    ):  # Apply changes to file only if there were relevant changes
        backup_file_path = file_path.with_suffix(file_path.suffix + BACKUP_FILES_SUFFIX)

        if not backup_file_path.exists():
            # Backup the original file on the first time it is configured (if the backup file doesn't exist)
            shutil.copyfile(file_path, backup_file_path)
            logger.info(
                f"Original configuration file was backed up to '{backup_file_path}'."
            )

        config_data.write(
            str(file_path), pretty_print=True, xml_declaration=True, encoding="utf-8"
        )
        logger.info(
            f"Configuration file ('{file_path}') was successfully configured for automatic module discovery. "
            f"New entries added: {added_entries_count}."
        )

    else:
        logger.info(
            f"All entries are already configured on the configuration file ('{file_path}'). No changes were made."
        )


def update_pycharm_config_xml_data(
    config_data: etree._ElementTree, python_discovery_paths: List[Path]
) -> int:
    """
    Configure and update the XML data within the configuration file
    to add the given python paths to the module discovery.

    Args:
        config_data (etree._ElementTree): The XML data to update
        python_discovery_paths (List[Path]): The python paths to add to the module discovery

    Returns:
        int: The number of added entries
    """
    url_prefix = "file://$MODULE_DIR$"
    module_root_manager_name = "NewModuleRootManager"
    module_root_manager_component = f"component[@name='{module_root_manager_name}']"
    module_root_manager_content = (
        f"{module_root_manager_component}/content[@url='{url_prefix}']"
    )

    # Generate the module root manager component if it doesn't exist
    if config_data.find(module_root_manager_component) is None:
        # Add spaces following last component
        root_data = config_data.getroot()

        module_root_manager_component_data = etree.SubElement(root_data, "component")
        module_root_manager_component_data.set("name", module_root_manager_name)

    # Generate the content component if it doesn't exist
    if config_data.find(module_root_manager_content) is None:
        # Add spaces following last content item
        module_root_manager_component_data = config_data.find(
            module_root_manager_component
        )

        etree.SubElement(module_root_manager_component_data, "content", url=url_prefix)

    source_folders = config_data.findall(module_root_manager_content + "/sourceFolder")
    existing_paths = set()

    for source_folder in source_folders:
        if url := source_folder.get("url"):
            existing_paths.add(Path(url.replace(f"{url_prefix}/", "")))

    module_root_manager_content_data = config_data.find(module_root_manager_content)
    added_entries_count = 0

    for python_path in python_discovery_paths:
        try:
            python_path_relative = python_path.relative_to(CONTENT_PATH)

        except ValueError:  # Skip paths that are not within the project root
            logger.debug(
                f"Skipping path '{python_path}' as it is not part of the project."
            )
            continue

        if python_path_relative in existing_paths:
            continue

        etree.SubElement(
            module_root_manager_content_data,
            "sourceFolder",
            url=f"{url_prefix}/{python_path_relative}",
            isTestSource="false",
        )
        added_entries_count += 1

    etree.indent(config_data)

    return added_entries_count


def configure_module_discovery(ide_type: IDEType):
    """
    Configure the IDE to auto discover CommonServerPython, demistomock, and API Modules files.

    Args:
        ide_type (IDEType): The IDE type to configure
    """
    if ide_type == IDEType.VSCODE:
        ide_folder = CONTENT_PATH / ".vscode"
        ide_folder.mkdir(exist_ok=True, parents=True)
        configure_vscode_settings(ide_folder=ide_folder)
        # Delete PYTHONPATH and MYPYPATH from env file because they are not needed
        env_file = CONTENT_PATH / ".env"
        env_vars = dotenv.dotenv_values(env_file)
        env_vars.pop("PYTHONPATH", None)
        env_vars.pop("MYPYPATH", None)
        update_dotenv(env_file, env_vars)

    if ide_type == IDEType.PYCHARM:
        python_discovery_paths = PYTHONPATH.copy()

        # Remove 'CONTENT_PATH' from the python discovery paths as it is already configured by default,
        # and all the configured paths are relative to the project root (which is 'CONTENT_PATH').
        if CONTENT_PATH in python_discovery_paths:
            python_discovery_paths.remove(CONTENT_PATH)

        config_file_path = CONTENT_PATH / ".idea" / f"{CONTENT_PATH.name.lower()}.iml"
        update_pycharm_config_file(
            file_path=config_file_path,
            python_discovery_paths=python_discovery_paths,
        )


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
            test_docker_image, command=["pip list --format=freeze"], remove=True
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
            update_dotenv(
                file_path=DOTENV_PATH,
                values={"DEMISTO_PARAMS": json.dumps(params)},
                quote_mode="never",
            )
        except SecretManagerException:
            logger.warning(
                f"Failed to fetch integration params for '{secret_id}' from Google Secret Manager."
            )

    else:
        logger.info(
            "Skipping Google Secret Manager lookup as 'DEMISTO_SDK_GCP_PROJECT_ID' environment variable is not set."
        )


def upload_and_create_instance(
    integration_script: Integration, instance_name: str, params: dict, test_module: bool
):
    client = get_client_from_server_type()
    pack = integration_script.in_pack
    assert isinstance(pack, Pack)
    with tempfile.TemporaryDirectory() as temp_dir:
        pack.upload(
            client=client.xsoar_client,
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
    ide: IDEType,
    file_path: Path,
    create_virtualenv: bool,
    overwrite_virtualenv: bool,
    secret_id: Optional[str],
    instance_name: Optional[str],
    test_module: bool,
):
    """Configures the environment of the integration

    Args:
        ide (IDEType): The IDE to configure to
        file_path (Path): The filepath of the integration
        create_virtualenv (bool): Whether create a virtual environment
        overwrite_virtualenv (bool): Whether overwrite the virtual environment
        secret_id (Optional[str]): The secret id to use
        instance_name (Optional[str]): The instance name to configure on XSOAR/XSIAM. If None, will not configure.
        test_module (bool): Whether run test module on the instance on XSOAR/XSIAM

    Raises:
        RuntimeError: If using auto-detection for IDE and it failed,
            or if the configuration failed (for instance, Docker is turned off)
    """
    base_path = CONTENT_PATH

    integration_script = BaseContent.from_path(Path(file_path))
    assert isinstance(
        integration_script, IntegrationScript
    ), "Expected Integration Script"
    add_demistomock_and_commonserveruser(integration_script)
    docker_image: Union[str, DockerImage] = integration_script.docker_image
    interpreter_path = CONTENT_PATH / ".venv" / "bin" / "python"
    configure_params(integration_script, secret_id, instance_name, test_module)
    if not docker_image:
        docker_image = DEF_DOCKER
    try:
        docker_helper.init_global_docker_client()
    except docker_helper.DockerException:
        logger.error(
            "Failed to initialize Docker client. Please assure Docker is running and properly configured."
        )
        raise
    (test_docker_image, errors,) = docker_helper.get_docker().get_or_create_test_image(
        docker_image, integration_script.type
    )
    if errors:
        raise RuntimeError(
            f"Failed to pull / create test Docker image for '{docker_image}': {errors}"
        )

    if create_virtualenv and integration_script.type.startswith("python"):
        pack = integration_script.in_pack
        assert isinstance(pack, Pack), "Expected pack"
        base_path = pack.path
        pack_env_file = base_path / ".env"
        if pack_env_file.exists() and not pack_env_file.is_symlink():
            pack_env_file.unlink(missing_ok=True)
        if not pack_env_file.exists():
            pack_env_file.symlink_to(DOTENV_PATH)
        if create_virtualenv and integration_script.type.startswith("python"):
            interpreter_path = install_virtualenv(
                integration_script, test_docker_image, overwrite_virtualenv
            )

    if ide == IDEType.VSCODE:
        configure_vscode(
            ide_folder=base_path / ".vscode",
            integration_script=integration_script,
            test_docker_image=test_docker_image,
            interpreter_path=interpreter_path,
        )


def clean_repo():
    """
    Clean the repository from temporary files like 'CommonServerPython' and API modules created by the 'lint' command.
    """
    for path in PYTHONPATH:
        for temp_file in CONTENT_PATH.rglob(f"{path.name}.py"):
            if temp_file.parent != path:
                temp_file.unlink(missing_ok=True)
    for path in CONTENT_PATH.rglob("*.pyc"):
        path.unlink(missing_ok=True)
    for path in CONTENT_PATH.rglob("test_data/__init__.py"):
        path.unlink(missing_ok=True)


def setup_env(
    file_paths: Tuple[Path, ...],
    ide_type: IDEType,
    create_virtualenv: bool = False,
    overwrite_virtualenv: bool = False,
    secret_id: Optional[str] = None,
    instance_name: Optional[str] = None,
    test_module: bool = False,
    clean: bool = False,
) -> None:
    """
    This function sets up the development environment for integration scripts

    Args:
        file_paths (Tuple[Path, ...]): File paths to set integration
        ide_type (IDEType): An IDEType value representing an IDE setup the environment for.
        create_virtualenv (bool, optional): Whether create virtual environment or not. Defaults to False.
        overwrite_virtualenv (bool, optional): Whether overwrite the existing virtual environment. Defaults to False.
        secret_id (Optional[str], optional): The secret id try to fetch from Google Secret Manager. Defaults to the integration name. Defaults to None.
        instance_name (Optional[str], optional): The instance name to configure on XSOAR/XSIAM. Defaults to None.
        test_module (bool, optional): Whether test-module will run or not. Defaults to False.
        clean (bool, optional): Whether clean the repository from temporary files. Defaults to False.

    Raises:
        RuntimeError:
    """
    if clean:
        clean_repo()

    configure_module_discovery(ide_type=ide_type)
    if not file_paths:
        (CONTENT_PATH / "CommonServerUserPython.py").touch()
        if ide_type == IDEType.VSCODE:
            ide_folder = CONTENT_PATH / ".vscode"
            ide_folder.mkdir(exist_ok=True)
            configure_vscode_settings(ide_folder=ide_folder)
    for file_path in file_paths:
        configure_integration(
            ide=ide_type,
            file_path=file_path,
            create_virtualenv=create_virtualenv,
            overwrite_virtualenv=overwrite_virtualenv,
            secret_id=secret_id,
            instance_name=instance_name,
            test_module=test_module,
        )
