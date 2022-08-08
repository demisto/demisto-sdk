import shlex
import shutil
import requests
from requests.adapters import HTTPAdapter, Retry

from datetime import datetime
from pathlib import Path
from typing import Any, List, TextIO

from demisto_sdk.commands.content_graph.content_graph_builder import ContentGraphBuilder
from demisto_sdk.commands.content_graph.interface.neo4j_graph import Neo4jContentGraphInterface
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.content.content import Content
from demisto_sdk.commands.common.tools import run_command

import docker
import logging


DATABASE_URL = 'bolt://localhost:7687'
USERNAME = 'neo4j'
NEO4J_PASSWORD = 'test'
REPO_PATH = Path(GitUtil(Content.git()).git_path())
BATCH_SIZE = 10000
IMPORT_PATH = REPO_PATH / 'neo4j' / 'import'

logger = logging.getLogger('demisto-sdk')


class Neo4jContentGraphBuilder(ContentGraphBuilder):
    def __init__(
        self,
        repo_path: Path,
        use_docker: bool = True,
        keep_service: bool = False,
        load_graph: bool = False,
        dump_on_exit: bool = False,
    ) -> None:
        super().__init__(repo_path)
        self.start_time = datetime.now()
        self.end_time = None
        self._content_graph = Neo4jContentGraphInterface(DATABASE_URL, auth=(USERNAME, NEO4J_PASSWORD))
        self.use_docker = use_docker
        self.keep_service = keep_service
        self.load_graph = load_graph
        self.dump_on_exit = dump_on_exit

    @property
    def content_graph(self) -> Neo4jContentGraphInterface:
        return self._content_graph

    def __enter__(self):
        if self.load_graph:
            self.load()
        self.start_neo4j_service()
        return self

    def start_neo4j_service(self, ):
        if not self.use_docker:
            run_command(f'neo4j-admin set-initial-password {NEO4J_PASSWORD}', cwd=REPO_PATH / 'neo4j', is_silenced=False)
            run_command('neo4j start', cwd=REPO_PATH / 'neo4j', is_silenced=False)

        else:
            docker_client = docker.from_env()
            try:
                docker_client.containers.get('neo4j-content').remove(force=True)
            except Exception as e:
                logger.info(f'Could not remove neo4j container: {e}')
            # then we need to create a new one
            run_command('docker-compose up -d', cwd=REPO_PATH / 'neo4j', is_silenced=False)
        # health check to make sure that neo4j is up
        s = requests.Session()

        retries = Retry(
            total=10,
            backoff_factor=0.1
        )

        s.mount('http://localhost', HTTPAdapter(max_retries=retries))
        s.get('http://localhost:7474')

    def stop_neo4j_service(self, ):
        if not self.use_docker:
            run_command('neo4j stop', cwd=REPO_PATH / 'neo4j', is_silenced=False)
        else:
            run_command('docker-compose down', cwd=REPO_PATH / 'neo4j', is_silenced=False)

    def neo4j_admin_command(self, name: str, command: str):
        if not self.use_docker:
            run_command(command, cwd=REPO_PATH / 'neo4j', is_silenced=False)
        else:
            docker_client = docker.from_env()
            try:
                docker_client.containers.get(f'neo4j-{name}').remove(force=True)
            except Exception as e:
                logger.info(f'Could not remove neo4j container: {e}')
            docker_client.containers.run(image='neo4j/neo4j-admin:4.4.9',
                                         name=f'neo4j-{name}',
                                         remove=True,
                                         volumes=[f'{REPO_PATH}/neo4j/data:/data', f'{REPO_PATH}/neo4j/backups:/backups'],
                                         command=shlex.split(command),
                                         )

    def dump(self):
        if self.use_docker:
            output = '/backups/content-graph.dump'
        else:
            (REPO_PATH / 'neo4j' / 'backups').mkdir(parents=True, exist_ok=True)
            output = (REPO_PATH / 'neo4j' / 'backups' / 'content-graph.dump').as_posix()
        self.neo4j_admin_command('dump', f'neo4j-admin dump --database=neo4j --to={output}')

    def load(self):
        if self.use_docker:
            shutil.rmtree(REPO_PATH / 'neo4j' / 'data', ignore_errors=True)
            output = '/backups/content-graph.dump'
        else:
            # todo delete data folder in host (should get it somehow)
            output = (REPO_PATH / 'neo4j' / 'backups' / 'content-graph.dump').as_posix()

        self.neo4j_admin_command('load', f'neo4j-admin load --database=neo4j --from={output}')

    def delete_modified_packs_from_graph(self, packs: List[str]) -> None:
        pass  # todo

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        # self.driver.close()
        if not self.keep_service:
            self.stop_neo4j_service()

        if self.dump_on_exit:
            self.dump()


def create_content_graph(use_docker: bool = True, keep_service: bool = False) -> None:
    shutil.rmtree(REPO_PATH / 'neo4j' / 'data', ignore_errors=True)
    with Neo4jContentGraphBuilder(REPO_PATH, use_docker, keep_service=keep_service, dump_on_exit=True) as content_graph:
        content_graph.create_graph_from_repository()


def load_content_graph(use_docker: bool = True, keep_service: bool = False, content_graph_path: Path = None) -> None:
    if content_graph_path and content_graph_path.is_file():
        shutil.copy(content_graph_path, REPO_PATH / 'neo4j' / 'backups' / 'content-graph.dump')

    with Neo4jContentGraphBuilder(REPO_PATH, use_docker, keep_service, load_graph=True):
        logger.info('Content Graph was loaded')
