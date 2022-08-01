from abc import ABC, abstractmethod
import csv
import multiprocessing
import shutil
import requests
from requests.adapters import HTTPAdapter, Retry

import urllib3

import neo4j
import pickle

from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple, Iterator, Dict

from demisto_sdk.commands.content_graph.constants import PACKS_FOLDER, ContentTypes, Rel
from demisto_sdk.commands.content_graph.parsers.pack import PackSubGraphCreator
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.content.content import Content
from demisto_sdk.commands.common.tools import run_command

import docker
import logging


DATABASE_URL = 'bolt://localhost:7687'
USERNAME = 'neo4j'
PASSWORD = 'test'
REPO_PATH = Path(GitUtil(Content.git()).git_path())
BATCH_SIZE = 10000
IMPORT_PATH = REPO_PATH / 'neo4j' / 'import'

logger = logging.getLogger('demisto-sdk')


def load_pickle(url: str) -> Any:
    try:
        with open(url, 'rb') as file:
            return pickle.load(file)
    except Exception:
        return {}


def dump_pickle(url: str, data: Any) -> None:
    with open(url, 'wb') as file:
        file.write(pickle.dumps(data))


class ContentGraph(ABC):
    def __init__(self, repo_path: Path) -> None:
        self.packs_path: Path = repo_path / PACKS_FOLDER
        self.nodes: Dict[ContentTypes, List[Dict[str, Any]]] = load_pickle('neo4j/nodes.pkl')
        self.relationships: Dict[Rel, List[Dict[str, Any]]] = load_pickle('neo4j/relationships.pkl')

    def parse_packs(self, packs_paths: Iterator[Path]) -> None:
        """ Parses packs into nodes and relationships by given paths. """
        if self.nodes and self.relationships:
            print('Skipping parsing.')
            return
        pool = multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1)
        for pack_nodes, pack_relationships in pool.map(PackSubGraphCreator.from_path, packs_paths):
            self.extend_graph_nodes_and_relationships(pack_nodes, pack_relationships)

    def extend_graph_nodes_and_relationships(
        self,
        pack_nodes: Dict[ContentTypes, List[Dict[str, Any]]],
        pack_relationships: Dict[Rel, List[Dict[str, Any]]],
    ) -> None:
        for content_type in ContentTypes:
            if content_type not in self.nodes:
                self.nodes[content_type] = []
            self.nodes[content_type].extend(pack_nodes.get(content_type, []))
        for rel in Rel:
            if rel not in self.relationships:
                self.relationships[rel] = []
            self.relationships[rel].extend(pack_relationships.get(rel, []))

    def parse_repository(self) -> None:
        """ Parses all repository packs into nodes and relationships. """
        self.clean_graph()
        all_packs_paths = self.iter_packs()
        self.parse_packs(all_packs_paths)
        self.add_parsed_nodes_and_relationships_to_graph()

    @abstractmethod
    def clean_graph(self) -> None:
        pass

    def iter_packs(self) -> Iterator[Path]:
        for path in self.packs_path.iterdir():  # todo: handle repo path is invalid
            if path.is_dir() and not path.name.startswith('.'):
                yield path

    @abstractmethod
    def add_parsed_nodes_and_relationships_to_graph(self) -> None:
        pass

    def build_modified_packs_paths(self, packs: List[str]) -> Iterator[Path]:
        for pack_id in packs:
            pack_path = Path(self.packs_path / pack_id)
            if not pack_path.is_dir():
                raise Exception(f'Could not find path of pack {pack_id}.')
            yield pack_path

    def parse_modified_packs(self) -> None:
        packs = self.get_modified_packs()
        self.delete_modified_packs_from_graph(packs)
        packs_paths = self.build_modified_packs_paths(packs)
        self.parse_packs(packs_paths)
        self.add_parsed_nodes_and_relationships_to_graph()

    @abstractmethod
    def delete_modified_packs_from_graph(self, packs: List[str]) -> None:
        pass

    def get_modified_packs(self) -> List[str]:
        return []  # todo


class Neo4jQuery:
    @staticmethod
    def create_nodes_indexes() -> List[str]:
        queries: List[str] = []
        template = 'CREATE INDEX ON :{label}({props})'
        constraints = ContentTypes.props_indexes()
        for label, props in constraints.items():
            props = ', '.join(props)
            queries.append(template.format(label=label, props=props))
        return queries

    @staticmethod
    def create_nodes_props_uniqueness_constraints() -> List[str]:
        queries: List[str] = []
        template = 'CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE {props} IS UNIQUE'
        constraints = ContentTypes.props_uniqueness_constraints()
        for label, props in constraints.items():
            props = ', '.join([f'n.{p}' for p in props])
            queries.append(template.format(label=label, props=props))
        return queries

    @staticmethod
    def create_nodes_props_existence_constraints() -> List[str]:
        queries: List[str] = []
        template = 'CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS NOT NULL'
        constraints = ContentTypes.props_existence_constraints()
        for label, props in constraints.items():
            for prop in props:
                queries.append(template.format(label=label, prop=prop))
        return queries

    @staticmethod
    def create_relationships_props_existence_constraints() -> List[str]:
        queries: List[str] = []
        template = 'CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:{label}]-() REQUIRE r.{prop} IS NOT NULL'
        constraints = Rel.props_existence_constraints()
        for label, props in constraints.items():
            for prop in props:
                queries.append(template.format(label=label, prop=prop))
        return queries

    @staticmethod
    def create_nodes_from_csv(content_type: ContentTypes) -> str:
        filename = f'file:///{content_type}.csv'
        return (
            f'UNWIND $data AS node_data '
            f'CREATE (n:{Neo4jQuery.labels_of(content_type)}{{node_id: node_data.node_id}}) SET n += node_data'
        )

    @staticmethod
    def create_has_command_relationships_from_csv() -> str:
        filename = f'file:///{Rel.HAS_COMMAND}.csv'
        return (
            f'UNWIND $data AS rel_data '
            f'MATCH (a:{ContentTypes.INTEGRATION}{{node_id: rel_data.from}}) '
            f'MERGE (b:{ContentTypes.COMMAND_OR_SCRIPT}{{id: rel_data.to}}) '
            f'ON CREATE SET b :{ContentTypes.COMMAND}, b.node_id = "{ContentTypes.COMMAND}:" + rel_data.to '
            f'MERGE (a)-[r:{Rel.HAS_COMMAND}]->(b) '
            'SET r.deprecated = rel_data.deprecated'  # todo: see todo in generic create
        )

    @staticmethod
    def create_executes_relationships_from_csv() -> str:
        # filename = f'file:///{Rel.EXECUTES}.csv'
        return (
            f'UNWIND $data AS rel_data '
            f'MATCH (a:{ContentTypes.SCRIPT}{{node_id: rel_data.from}}) '
            f'MERGE (b:{ContentTypes.COMMAND_OR_SCRIPT}{{id: rel_data.to}}) '
            f'MERGE (a)-[r:{Rel.EXECUTES}]->(b) '
            'SET r.deprecated = rel_data.deprecated'
            # todo: see todo in generic create
        )

    @staticmethod
    def create_tested_by_relationships_from_csv() -> str:
        filename = f'file:///{Rel.TESTED_BY}.csv'
        return (
            f'UNWIND $data AS rel_data '
            f'MATCH (a:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.from}}) '
            f'MERGE (b:{ContentTypes.TEST_PLAYBOOK}{{id: rel_data.to}}) '
            f'ON CREATE SET b.node_id = "{ContentTypes.TEST_PLAYBOOK}:" + rel_data.to '
            f'MERGE (a)-[r:{Rel.TESTED_BY}]->(b) '
        )

    @staticmethod
    def create_relationships_from_csv(rel_type: Rel) -> str:
        if rel_type == Rel.EXECUTES:
            return Neo4jQuery.create_executes_relationships_from_csv()
        if rel_type == Rel.HAS_COMMAND:
            return Neo4jQuery.create_has_command_relationships_from_csv()
        if rel_type == Rel.TESTED_BY:
            return Neo4jQuery.create_tested_by_relationships_from_csv()

        filename = f'file:///{rel_type}.csv'
        return (
            f'UNWIND $data AS rel_data '
            f'MATCH (a:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.from}}) '
            f'MERGE (b:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.to}}) '
            f'MERGE (a)-[r:{rel_type}]->(b) SET r = rel_data'  # todo: should be r += rel_data.props, update in parser
        )

    @staticmethod
    def create_pack_dependencies() -> str:
        return (
            ''
        )

    @staticmethod
    def export_nodes_by_type(content_type: ContentTypes) -> None:
        filename = f'{content_type}.csv'
        return (
            f'MATCH (n:{content_type}) '
            'WITH collect(n) AS nodes '
            f'CALL apoc.export.csv.data(nodes, [], "{filename}", {{}}) '
            'YIELD file, nodes, done '
            'RETURN file, nodes, done'
        )

    @staticmethod
    def export_relationships_by_type(rel_type: Rel) -> None:
        filename = f'{rel_type}.csv'
        return (
            f'MATCH ()-[n:{rel_type}]->() '
            'WITH collect(n) AS rels '
            f'CALL apoc.export.csv.data([], rels, "{filename}", {{}}) '
            'YIELD done '
            'RETURN done'
        )

    @staticmethod
    def labels_of(content_type: ContentTypes) -> str:
        return ':'.join(content_type.labels)


class Neo4jContentGraph(ContentGraph):
    def __init__(
        self,
        repo_path: Path,
        database_uri: str,
        user: str = None,
        password: str = None,
        use_docker: bool = True,
        keep_service: bool = False,
        dump_file: Path = None,
    ) -> None:
        super().__init__(repo_path)
        self.start_time = datetime.now()
        self.end_time = None
        auth: Optional[Tuple[str, str]] = (user, password) if user and password else None
        self.driver: neo4j.Neo4jDriver = neo4j.GraphDatabase.driver(database_uri, auth=auth)
        self.use_docker = use_docker
        self.keep_service = keep_service

    def __enter__(self):
        self.start_neo4j_service()
        return self

    def start_neo4j_service(self, ):
        if not self.use_docker:
            run_command(f'neo4j-admin set-initial-password {PASSWORD} && neo4j start', cwd=REPO_PATH / 'neo4j', is_silenced=False)

        else:
            docker_client = docker.from_env()
            try:
                docker_client.containers.get('neo4j-content').remove(force=True)
            except Exception as e:
                logger.info(f'Could not remove neo4j container: {e}')
            # then we need to create a new one
            shutil.rmtree(REPO_PATH / 'neo4j' / 'data', ignore_errors=True)
            shutil.rmtree(REPO_PATH / 'neo4j' / 'import', ignore_errors=True)
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
                                         volumes={f'{REPO_PATH}/neo4j/data': {'bind': '/data', 'mode': 'rw'},
                                                  f'{REPO_PATH}/neo4j/backups': {'bind': '/backups', 'mode': 'rw'}},

                                         command=f'{command}'
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
            output = (REPO_PATH / 'neo4j' / 'backups' / 'content-graph.dump').as_posix()

        self.neo4j_admin_command('load', f'neo4j-admin load --from={output}')

    @staticmethod
    def create_indexes(tx: neo4j.Transaction) -> None:
        queries: List[str] = []
        queries.extend(Neo4jQuery.create_nodes_indexes())
        for query in queries:
            print('Running query:' + query)
            tx.run(query)

    @staticmethod
    def create_constraints(tx: neo4j.Transaction) -> None:
        queries: List[str] = []
        queries.extend(Neo4jQuery.create_nodes_props_uniqueness_constraints())
        # queries.extend(Neo4jQuery.create_nodes_props_existence_constraints())
        # queries.extend(Neo4jQuery.create_relationships_props_existence_constraints())
        for query in queries:
            print('Running query:' + query)
            tx.run(query)

    def clean_graph(self) -> None:
        pass  # todo

    def delete_modified_packs_from_graph(self, packs: List[str]) -> None:
        pass  # todo

    def add_parsed_nodes_and_relationships_to_graph(self) -> None:
        # init driver

        before_creating_nodes = datetime.now()
        print(f'Time since started: {(before_creating_nodes - self.start_time).total_seconds() / 60} minutes')

        dump_pickle('neo4j/nodes.pkl', self.nodes)
        dump_pickle('neo4j/relationships.pkl', self.relationships)

        with self.driver.session() as session:
            tx = session.begin_transaction()
            self.create_indexes(tx)
            self.create_constraints(tx)
            tx.commit()
            tx.close()
            for content_type in ContentTypes.non_abstracts():  # todo: parallelize?
                if self.nodes.get(content_type):
                    session.write_transaction(self.import_nodes_by_type, content_type)
            for rel in Rel:
                if self.relationships.get(rel):  # todo: parallelize?
                    session.write_transaction(self.import_relationships_by_type, rel)
            # session.write_transaction(self.create_pack_dependencies_relationships)

        after_creating_nodes = datetime.now()
        print(f'Time to create graph: {(after_creating_nodes - before_creating_nodes).total_seconds() / 60} minutes')
        print(f'Time since started: {(after_creating_nodes - self.start_time).total_seconds() / 60} minutes')

    # def create_node_csv_file(self, content_type: ContentTypes) -> bool:
    #     if self.nodes.get(content_type):
    #         headers = list(sorted(self.nodes.get(content_type)[0].keys()))
    #         with open(f'{IMPORT_PATH}/{content_type}.csv', 'w', encoding='utf-8') as f:
    #             writer = csv.writer(f)
    #             writer.writerow(headers)
    #             for row in self.nodes.get(content_type):
    #                 writer.writerow([row[k] for k in sorted(row.keys())])
    #         return True
    #     return False

    # def create_relationship_csv_file(self, rel: Rel) -> bool:
    #     if self.relationships.get(rel):
    #         headers = list(sorted(self.relationships.get(rel)[0].keys()))
    #         with open(f'{IMPORT_PATH}/{rel.value}.csv', 'w', encoding='utf-8') as f:
    #             writer = csv.writer(f)
    #             writer.writerow(headers)
    #             for row in self.relationships.get(rel):
    #                 writer.writerow([row[k] for k in sorted(row.keys())])
    #         return True
    #     return False

    def import_nodes_by_type(self, tx: neo4j.Transaction, content_type: ContentTypes) -> None:
        query = Neo4jQuery.create_nodes_from_csv(content_type)
        tx.run(query, {'data': self.nodes.get(content_type)})
        print(f'Imported {content_type}.csv')

    def import_relationships_by_type(self, tx: neo4j.Transaction, rel_type: Rel) -> None:
        query = Neo4jQuery.create_relationships_from_csv(rel_type)
        tx.run(query, {'data': self.relationships.get(rel_type)})
        print(f'Imported {rel_type}')

    @staticmethod
    def create_pack_dependencies_relationships(tx: neo4j.Transaction) -> None:
        query = Neo4jQuery.create_pack_dependencies()
        tx.run(query)
        print('Created dependencies between packs.')

    @staticmethod
    def export_nodes_by_type(tx: neo4j.Transaction, content_type: ContentTypes) -> None:
        query = Neo4jQuery.export_nodes_by_type(content_type)
        result = tx.run(query).single()
        print(result['done'])

    @staticmethod
    def export_relationships_by_type(tx: neo4j.Transaction, rel_type: Rel) -> None:
        query = Neo4jQuery.export_relationships_by_type(rel_type)
        result = tx.run(query).single()
        print(result['done'])

    def export_all(self) -> None:
        with self.driver.session() as session:
            for content_type in ContentTypes.non_abstracts():
                session.write_transaction(self.export_nodes_by_type, content_type)
            for rel in Rel:
                session.write_transaction(self.export_relationships_by_type, rel)

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.driver.close()
        if not self.keep_service:
            self.stop_neo4j_service()


def create_content_graph(use_docker: bool = True) -> None:
    with Neo4jContentGraph(REPO_PATH, DATABASE_URL, USERNAME, PASSWORD, use_docker) as content_graph:
        content_graph.parse_repository()
    content_graph.dump()


def load_content_graph(use_docker: bool = True, keep_service: bool = False) -> None:
    content_graph = Neo4jContentGraph(REPO_PATH, DATABASE_URL, USERNAME, PASSWORD, use_docker, keep_service)
    content_graph.load()
    content_graph.start_neo4j_service()
    if not keep_service:
        content_graph.stop_neo4j_service()
