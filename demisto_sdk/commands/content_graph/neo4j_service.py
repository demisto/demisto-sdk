import hashlib
import logging
from pathlib import Path

import docker
import requests

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.docker_helper import init_global_docker_client
from demisto_sdk.commands.content_graph.common import (
    NEO4J_DATABASE_HTTP,
    NEO4J_FOLDER,
    NEO4J_PASSWORD,
)

REPO_PATH = CONTENT_PATH

NEO4J_VERSION = "4.4.12"

NEO4J_SERVICE_IMAGE = f"neo4j:{NEO4J_VERSION}"

LOCAL_NEO4J_PATH = Path("/var/lib/neo4j")
NEO4J_IMPORT_FOLDER = "import"
NEO4J_DATA_FOLDER = "data"
NEO4J_PLUGINS_FOLDER = "plugins"

# When updating the APOC version, make sure to update the checksum as well
APOC_URL_VERSIONS = (
    "https://neo4j-contrib.github.io/neo4j-apoc-procedures/versions.json"
)

logger = logging.getLogger("demisto-sdk")


class Neo4jServiceException(Exception):
    pass


def _stop_neo4j_service_docker(docker_client: docker.DockerClient):
    """Helper function to stop the neo4j service docker container

    Args:
        docker_client (docker.DockerClient): The docker client to use
    """
    try:
        neo4j_docker = docker_client.containers.get("neo4j-content")
        if not neo4j_docker:
            return
        neo4j_docker.stop()
        neo4j_docker.remove(force=True)
    except Exception as e:
        logger.debug(f"Could not remove neo4j container: {e}")


def _is_apoc_available(plugins_path: Path, sha1: str) -> bool:
    for plugin in plugins_path.iterdir():
        if (
            plugin.name.startswith("apoc")
            and hashlib.sha1(plugin.read_bytes()).hexdigest() == sha1
        ):
            return True
    return False


def _download_apoc():
    apocs = [
        apoc
        for apoc in requests.get(APOC_URL_VERSIONS, verify=False).json()
        if apoc["neo4j"] == NEO4J_VERSION
    ]
    if not apocs:
        logger.debug(f"Could not find APOC for neo4j version {NEO4J_VERSION}")
        return
    download_url = apocs[0].get("downloadUrl")
    sha1 = apocs[0].get("sha1")
    plugins_folder = REPO_PATH / NEO4J_FOLDER / NEO4J_PLUGINS_FOLDER
    plugins_folder.mkdir(parents=True, exist_ok=True)

    if _is_apoc_available(plugins_folder, sha1):
        logger.debug("APOC is already available, skipping installation")
        return
    logger.info("Downloading APOC plugin, please wait...")
    # Download APOC_URL and save it to plugins folder in neo4j
    response = requests.get(download_url, verify=False, stream=True)

    with open(plugins_folder / "apoc.jar", "wb") as f:
        f.write(response.content)


def start():
    """Starting the neo4j service

    Args:
    """
    if is_alive():
        return

    Path.mkdir(REPO_PATH / NEO4J_FOLDER, exist_ok=True, parents=True)
    # we download apoc only if we are running on docker
    # if the user is running locally he needs to setup apoc manually
    _download_apoc()
    docker_client = init_global_docker_client()
    _stop_neo4j_service_docker(docker_client)
    docker_client.containers.run(
        image=NEO4J_SERVICE_IMAGE,
        name="neo4j-content",
        ports={"7474/tcp": 7474, "7687/tcp": 7687, "7473/tcp": 7473},
        volumes=[
            f"{REPO_PATH / NEO4J_FOLDER / NEO4J_DATA_FOLDER}:/{NEO4J_DATA_FOLDER}",
            f"{REPO_PATH / NEO4J_FOLDER / NEO4J_IMPORT_FOLDER}:{LOCAL_NEO4J_PATH / NEO4J_IMPORT_FOLDER}",
            f"{REPO_PATH / NEO4J_FOLDER / NEO4J_PLUGINS_FOLDER}:/{NEO4J_PLUGINS_FOLDER}",
        ],
        detach=True,
        environment={
            "NEO4J_AUTH": f"neo4j/{NEO4J_PASSWORD}",
            "NEO4J_apoc_export_file_enabled": "true",
            "NEO4J_apoc_import_file_enabled": "true",
            "NEO4J_apoc_import_file_use__neo4j__config": "true",
            "NEO4J_dbms_security_procedures_unrestricted": "apoc.*",
            "NEO4J_dbms_security_procedures_allowlist": "apoc.*",
        },
        healthcheck={
            "test": f"curl --fail {NEO4J_DATABASE_HTTP} || exit 1",
            "interval": 5 * 1000000000,
            "timeout": 15 * 1000000000,
            "retries": 10,
        },
    )


def stop():
    """Stop the neo4j service"""
    if not is_alive():
        return
    if not is_running_on_docker():
        logger.debug("Neo4j is running locally. Stop with `neo4j stop`")
        return
    docker_client = init_global_docker_client()
    _stop_neo4j_service_docker(docker_client)


def is_alive():
    try:
        return requests.get(NEO4J_DATABASE_HTTP, timeout=10).ok
    except requests.exceptions.RequestException:
        return False


def is_running_on_docker():
    return not LOCAL_NEO4J_PATH.exists()


def get_neo4j_import_path() -> Path:
    if not is_running_on_docker():
        return LOCAL_NEO4J_PATH / NEO4J_IMPORT_FOLDER
    return REPO_PATH / NEO4J_FOLDER / NEO4J_IMPORT_FOLDER
