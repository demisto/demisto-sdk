import logging

import docker
import requests
import urllib3
from demisto_sdk.commands.common.tools import run_command
from requests.adapters import HTTPAdapter, Retry

from demisto_sdk.commands.content_graph.common import NEO4J_PASSWORD, REPO_PATH

NEO4J_SERVICE_IMAGE = 'neo4j:4.4.9'
NEO4J_ADMIN_IMAGE = 'neo4j/neo4j-admin:4.4.9'

logger = logging.getLogger('demisto-sdk')

try:
    run_command('neo4j-admin --version', cwd=REPO_PATH / 'neo4j', is_silenced=True)
    IS_NEO4J_ADMIN_AVAILABLE = True
except Exception:
    IS_NEO4J_ADMIN_AVAILABLE = False


class Neo4jServiceException(Exception):
    pass


def _get_docker_client() -> docker.DockerClient:
    try:
        docker_client = docker.from_env()
    except docker.errors.DockerException:
        msg = 'Could not connect to docker daemon. Please make sure docker is running.'
        raise Neo4jServiceException(msg)
    return docker_client


def _stop_neo4j_service_docker(docker_client: docker.DockerClient):
    try:
        docker_client.containers.get('neo4j-content').remove(force=True)
    except Exception as e:
        logger.info(f'Could not remove neo4j container: {e}')


def _wait_until_service_is_up():
    s = requests.Session()

    retries = Retry(
        total=10,
        backoff_factor=0.1
    )
    # suppress warning from urllib3
    # urllib3.disable_warnings(urllib3.exceptions.ConnectionError)
    s.mount('http://localhost', HTTPAdapter(max_retries=retries))
    s.get('http://localhost:7474')


def start_neo4j_service(use_docker: bool = True):
    if not use_docker:
        neo4j_admin_command('set-initial-password', f'neo4j - admin set - initial - password {NEO4J_PASSWORD}')
        run_command('neo4j start', cwd=REPO_PATH / 'neo4j', is_silenced=False)

    else:
        docker_client = _get_docker_client()
        _stop_neo4j_service_docker(docker_client)
        docker_client.containers.run(
            image=NEO4J_SERVICE_IMAGE,
            name='neo4j-content',
            ports={'7474/tcp': 7474, '7687/tcp': 7687, '7473/tcp': 7473},
            volumes=[f'{REPO_PATH / "neo4j" / "data"}:/data'],
            detach=True,
            environment={'NEO4J_AUTH': f'neo4j/{NEO4J_PASSWORD}'},
        )
    # health check to make sure that neo4j is up
    _wait_until_service_is_up()


def stop_neo4j_service(use_docker: bool):
    if not use_docker:
        run_command('neo4j stop', cwd=REPO_PATH / 'neo4j', is_silenced=False)
    else:
        docker_client = _get_docker_client()
        _stop_neo4j_service_docker(docker_client)


def neo4j_admin_command(name: str, command: str):
    if IS_NEO4J_ADMIN_AVAILABLE:
        run_command(command, cwd=REPO_PATH / 'neo4j', is_silenced=False)
    else:
        docker_client = docker.from_env()
        try:
            docker_client.containers.get(f'neo4j-{name}').remove(force=True)
        except Exception as e:
            logger.info(f'Could not remove neo4j container: {e}')
        docker_client.containers.run(image=NEO4J_ADMIN_IMAGE,
                                     name=f'neo4j-{name}',
                                     remove=True,
                                     volumes=[f'{REPO_PATH}/neo4j/data:/data', f'{REPO_PATH}/neo4j/backups:/backups'],
                                     command=command,
                                     )


def dump():
    command = f'neo4j-admin dump --database=neo4j --to={"/backups/content-graph.dump" if IS_NEO4J_ADMIN_AVAILABLE else REPO_PATH / "neo4" / "content-graph.dump"}'
    neo4j_admin_command('dump', command)


def load():
    command = f'neo4j-admin load --database=neo4j --from={"/backups/content-graph.dump" if IS_NEO4J_ADMIN_AVAILABLE else REPO_PATH / "neo4" / "content-graph.dump"}'
    neo4j_admin_command('load', command)
