import logging
import shutil
from pathlib import Path

import docker
import requests
from requests.adapters import HTTPAdapter, Retry

from demisto_sdk.commands.common.tools import run_command
from demisto_sdk.commands.content_graph.common import (NEO4J_DATABASE_HTTP,
                                                       NEO4J_PASSWORD,
                                                       REPO_PATH)

NEO4J_SERVICE_IMAGE = "neo4j:4.4.12"
NEO4J_ADMIN_IMAGE = "neo4j/neo4j-admin:4.4.12"

logger = logging.getLogger("demisto-sdk")

try:
    run_command("neo4j-admin --version", cwd=REPO_PATH, is_silenced=True)
    logger.info("Using local neo4j-admin")
    IS_NEO4J_ADMIN_AVAILABLE = True
except Exception:
    logger.info("Could not find neo4j-admin in path. Using docker instead.")
    IS_NEO4J_ADMIN_AVAILABLE = False


class Neo4jServiceException(Exception):
    pass


def _get_docker_client() -> docker.DockerClient:
    """Helper function to get the docker client

    Raises:
        Neo4jServiceException: If docker is not available in the system.

    Returns:
        docker.DockerClient: The docker client to use
    """
    try:
        docker_client = docker.from_env()
    except docker.errors.DockerException:
        msg = "Could not connect to docker daemon. Please make sure docker is running."
        raise Neo4jServiceException(msg)
    return docker_client


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
        logger.info(f"Could not remove neo4j container: {e}")


def _wait_until_service_is_up():
    """Helper function to wait until service is up"""
    s = requests.Session()

    retries = Retry(total=10, backoff_factor=0.1)
    s.mount(NEO4J_DATABASE_HTTP, HTTPAdapter(max_retries=retries))
    s.get(NEO4J_DATABASE_HTTP)


def _should_use_docker(use_docker: bool) -> bool:
    return use_docker or not IS_NEO4J_ADMIN_AVAILABLE


def start(use_docker: bool = True):
    """Starting the neo4j service

    Args:
        use_docker (bool, optional): Whether use docker or run locally. Defaults to True.
    """
    use_docker = _should_use_docker(use_docker)
    if not use_docker:
        _neo4j_admin_command(
            "set-initial-password", f"neo4j-admin set-initial-password {NEO4J_PASSWORD}"
        )
        run_command("neo4j start", cwd=REPO_PATH, is_silenced=False)

    else:
        Path.mkdir(REPO_PATH / "neo4j-data", exist_ok=True, parents=True)
        docker_client = _get_docker_client()
        _stop_neo4j_service_docker(docker_client)
        docker_client.containers.run(
            image=NEO4J_SERVICE_IMAGE,
            name="neo4j-content",
            ports={"7474/tcp": 7474, "7687/tcp": 7687, "7473/tcp": 7473},
            volumes=[f'{REPO_PATH / "neo4j-data" / "data"}:/data'],
            detach=True,
            environment={"NEO4J_AUTH": f"neo4j/{NEO4J_PASSWORD}"},
        )
    # health check to make sure that neo4j is up
    _wait_until_service_is_up()


def stop(use_docker: bool):
    """Stop the neo4j service

    Args:
        use_docker (bool): Whether stop the sercive using docker or not.
    """
    use_docker = _should_use_docker(use_docker)
    if not use_docker:
        run_command("neo4j stop", cwd=REPO_PATH, is_silenced=False)
    else:
        docker_client = _get_docker_client()
        _stop_neo4j_service_docker(docker_client)


def _neo4j_admin_command(name: str, command: str):
    """Helper function to run neo4j admin command

    Args:
        name (str): name of the command
        command (str): The neo4j admin command to run
    """
    if IS_NEO4J_ADMIN_AVAILABLE:
        run_command(command, cwd=REPO_PATH, is_silenced=False)
    else:
        docker_client = _get_docker_client()
        try:
            neo4j_container = docker_client.containers.get(f"neo4j-{name}")
            if neo4j_container:
                neo4j_container.remove(force=True)
        except Exception as e:
            logger.info(f"Could not remove neo4j container: {e}")
        docker_client.containers.run(
            image=NEO4J_ADMIN_IMAGE,
            name=f"neo4j-{name}",
            remove=True,
            volumes=[
                f"{REPO_PATH}/neo4j-data/data:/data",
                f"{REPO_PATH}/neo4j-data/backups:/backups",
            ],
            command=command,
        )


def dump(output_path: Path, use_docker=True):
    """Dump the content graph to a file"""
    use_docker = _should_use_docker(use_docker)
    stop(use_docker)
    dump_path = Path("/backups/content-graph.dump") if use_docker else output_path
    command = f"neo4j-admin dump --database=neo4j --to={dump_path}"
    # The actual path in the host is different than the path in the container
    real_path = (
        (REPO_PATH / "neo4j-data" / "backups" / "content-graph.dump")
        if use_docker
        else output_path
    )
    real_path.unlink(missing_ok=True)
    _neo4j_admin_command("dump", command)
    if use_docker:
        # since we have to save the dump in the container, we need to copy the correct path to the host
        shutil.copy(real_path, output_path)
    start(use_docker)


def load(input_path: Path, use_docker=True):
    """Load the content graph from a file"""
    use_docker = _should_use_docker(use_docker)
    stop(use_docker)
    dump_path = Path("/backups/content-graph.dump") if use_docker else input_path
    if use_docker:
        # remove existing data
        Path.mkdir(REPO_PATH / "neo4j-data" / "backups", parents=True, exist_ok=True)
        shutil.rmtree(REPO_PATH / "neo4j-data" / "data", ignore_errors=True)
        # copy the dump file to the correct path
        shutil.copy(input_path, REPO_PATH / "neo4j" / "backups" / "content-graph.dump")
    # currently we assume that the data is empty when running without docker
    command = f"neo4j-admin load --database=neo4j --from={dump_path}"
    _neo4j_admin_command("load", command)
    start(use_docker)


def is_alive():
    try:
        return requests.get(NEO4J_DATABASE_HTTP, timeout=10).ok
    except requests.exceptions.RequestException:
        return False
