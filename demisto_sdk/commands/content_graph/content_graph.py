from abc import ABC, abstractmethod
import csv
import multiprocessing
import shutil
import time
import neo4j
import pickle

from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple, Iterator, Dict

from demisto_sdk.commands.content_graph.constants import PACKS_FOLDER, ContentTypes, Rel
from demisto_sdk.commands.content_graph.parsers.pack import PackSubGraphCreator
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.content.content import Content
from demisto_sdk.commands.common.tools import run_command_os

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
        return []


def dump_pickle(url: str, data: Any) -> None:
    with open(url, 'wb') as file:
        file.write(pickle.dumps(data))


class ContentGraph(ABC):
    def __init__(self, repo_path: Path) -> None:
        self.packs_path: Path = repo_path / PACKS_FOLDER
        self.nodes: Dict[ContentTypes, List[Dict[str, Any]]] = {}
        self.relationships: Dict[Rel, List[Dict[str, Any]]] = {}

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
            if path.is_dir():
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


class Neo4jContentGraph(ContentGraph):
    def __init__(self, repo_path: Path, database_uri: str, user: str = None, password: str = None) -> None:
        super().__init__(repo_path)
        self.start_time = datetime.now()
        self.end_time = None
        auth: Optional[Tuple[str, str]] = (user, password) if user and password else None
        self.driver: neo4j.Neo4jDriver = neo4j.GraphDatabase.driver(database_uri, auth=auth)

    def __enter__(self):
        with self.driver.session() as session:
            tx = session.begin_transaction()
            self.create_constraints(tx)
            tx.commit()
            tx.close()
        return self

    def dump(self):
        docker_client = docker.from_env()
        try:
            docker_client.containers.get('neo4j-dump').remove(force=True)
        except Exception as e:
            logger.info(f'Could not remove neo4j-dump container: {e}')
        docker_client.containers.run(image='neo4j/neo4j-admin:4.4.9',
                                     remove=True,
                                     volumes={f'{REPO_PATH}/neo4j/data': {'bind': '/data', 'mode': 'rw'},
                                              f'{REPO_PATH}/neo4j/backups': {'bind': '/backups', 'mode': 'rw'}},

                                     command='neo4j-admin dump --database=neo4j --to=/backups/content-graph.dump'
                                     )

    def load(self):
        shutil.rmtree(REPO_PATH / 'neo4j' / 'data', ignore_errors=True)

        docker_client = docker.from_env()
        try:
            docker_client.containers.get('neo4j-load').remove(force=True)
        except Exception as e:
            logger.info(f'Could not remove neo4j-load container: {e}')
        # remove neo4j folder
        docker_client.containers.run(image='neo4j/neo4j-admin:4.4.9',
                                     name='neo4j-load',
                                     remove=True,
                                     volumes={f'{REPO_PATH}/neo4j/data': {'bind': '/data', 'mode': 'rw'},
                                              f'{REPO_PATH}/neo4j/backups': {'bind': '/backups', 'mode': 'rw'}},

                                     command='neo4j-admin load --database=neo4j --from=/backups/content-graph.dump'
                                     )

    @staticmethod
    def create_constraints(tx: neo4j.Transaction) -> None:
        queries: List[str] = []
        queries.extend(Neo4jContentGraph.build_nodes_props_uniqueness_queries())
        # queries.extend(Neo4jContentGraph.build_nodes_props_existence_queries())
        # queries.extend(Neo4jContentGraph.build_relationships_props_existence_queries())
        for query in queries:
            print(query)
            tx.run(query)

    @staticmethod
    def build_nodes_props_uniqueness_queries() -> List[str]:
        queries: List[str] = []
        template = 'CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE {props} IS UNIQUE'
        constraints = ContentTypes.props_uniqueness_constraints()
        for label, props in constraints.items():
            props = ', '.join([f'n.{p}' for p in props])
            queries.append(template.format(label=label, props=props))
        return queries

    @staticmethod
    def build_nodes_props_existence_queries() -> List[str]:
        queries: List[str] = []
        template = 'CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS NOT NULL'
        constraints = ContentTypes.props_existence_constraints()
        for label, props in constraints.items():
            for prop in props:
                queries.append(template.format(label=label, prop=prop))
        return queries

    @staticmethod
    def build_relationships_props_existence_queries() -> List[str]:
        queries: List[str] = []
        template = 'CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:{label}]-() REQUIRE r.{prop} IS NOT NULL'
        constraints = Rel.props_existence_constraints()
        for label, props in constraints.items():
            for prop in props:
                queries.append(template.format(label=label, prop=prop))
        return queries

    def clean_graph(self) -> None:
        pass  # todo

    def delete_modified_packs_from_graph(self, packs: List[str]) -> None:
        pass  # todo

    @staticmethod
    def import_nodes_by_type(tx: neo4j.Transaction, content_type: ContentTypes) -> None:
        filename = f'file:///{content_type}.csv'
        labels = ''.join([f':{label}' for label in content_type.labels])
        query = (
            f'LOAD CSV WITH HEADERS FROM "{filename}" AS node_data '
            f'CREATE (n{labels}{{node_id: node_data.node_id}}) SET n += node_data'
        )
        tx.run(query)
        print(f'Imported {filename}')

    @staticmethod
    def export_nodes_by_type(tx: neo4j.Transaction, content_type: ContentTypes) -> None:
        query = (
            'MATCH (n:$label) '
            'WITH collect(n) AS nodes '
            'CALL apoc.export.csv.data(nodes, [], "$filename", {}) '
            'YIELD file, nodes, done '
            'RETURN file, nodes, done'
        )
        result = tx.run(query, label=content_type.value, filename=f'{content_type.value}.csv').single()
        print(result['done'])

    @staticmethod
    def import_relationships_by_type(tx: neo4j.Transaction, rel_type: Rel) -> None:
        filename = f'file:///{rel_type}.csv'
        query = (
            f'LOAD CSV WITH HEADERS FROM "{filename}" AS rel_data '
            f'MATCH (a:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.from}}) '
            f'MERGE (b:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.to}}) '
            f'MERGE (a)-[r:{rel_type}]->(b) SET r += rel_data'
        )
        tx.run(query)
        print(f'Imported {filename}')

    @staticmethod
    def import_executes_relationships(tx: neo4j.Transaction) -> None:
        filename = f'file:///{Rel.EXECUTES}.csv'
        query = (
            f'LOAD CSV WITH HEADERS FROM "{filename}" AS rel_data '
            f'MATCH (a:{ContentTypes.SCRIPT}{{node_id: rel_data.from}}) '
            f'MERGE (b:{ContentTypes.COMMAND_OR_SCRIPT}{{id: rel_data.to}}) '
            f'MERGE (a)-[r:{Rel.EXECUTES}]->(b) SET r += rel_data'
        )
        tx.run(query)
        print(f'Imported {filename}')

    @staticmethod
    def import_has_command_relationships(tx: neo4j.Transaction) -> None:
        filename = f'file:///{Rel.HAS_COMMAND}.csv'
        query = (
            f'LOAD CSV WITH HEADERS FROM "{filename}" AS rel_data '
            f'MATCH (a:{ContentTypes.INTEGRATION}{{node_id: rel_data.from}}) '
            f'MERGE (b:{ContentTypes.COMMAND}{{node_id: rel_data.to}}) '
            f'MERGE (a)-[r:{Rel.HAS_COMMAND}]->(b) SET r += rel_data'
        )
        tx.run(query)
        print(f'Imported {filename}')

    @staticmethod
    def export_relationships_by_type(tx: neo4j.Transaction, rel_type: Rel) -> None:
        query = (
            'MATCH ()-[n:$rel]->() '
            'WITH collect(n) AS rels '
            'CALL apoc.export.csv.data([], rels, "$rel.csv", {}) '
            'YIELD done '
            'RETURN done'
        )
        result = tx.run(query, rel=rel_type.value, filename=f'{rel_type.value}.csv').single()
        print(result['done'])

    def export_all(self) -> None:
        with self.driver.session() as session:
            for content_type in ContentTypes.non_abstracts():
                session.write_transaction(self.export_nodes_by_type, content_type)
            for rel in Rel:
                session.write_transaction(self.export_relationships_by_type, rel)

    def create_node_csv_file(self, content_type: ContentTypes) -> bool:
        if self.nodes.get(content_type):
            headers = list(sorted(self.nodes.get(content_type)[0].keys()))
            with open(f'{IMPORT_PATH}/{content_type}.csv', 'w', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in self.nodes.get(content_type):
                    writer.writerow([row[k] for k in sorted(row.keys())])
            return True
        return False

    def create_relationship_csv_file(self, rel: Rel) -> bool:
        if self.relationships.get(rel):
            headers = list(sorted(self.relationships.get(rel)[0].keys()))
            with open(f'{IMPORT_PATH}/{rel.value}.csv', 'w', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in self.relationships.get(rel):
                    writer.writerow([row[k] for k in sorted(row.keys())])
            return True
        return False

    def add_parsed_nodes_and_relationships_to_graph(self) -> None:
        # dump_pickle('/Users/dtavori/dev/demisto/content-graph/nodes.pkl', self.nodes)
        # dump_pickle('/Users/dtavori/dev/demisto/content-graph/rels.pkl', self.relationships)
        before_creating_nodes = datetime.now()
        print(f'Time since started: {(before_creating_nodes - self.start_time).total_seconds() / 60} minutes')

        with self.driver.session() as session:
            for content_type in ContentTypes.non_abstracts():
                if self.create_node_csv_file(content_type):
                    session.write_transaction(self.import_nodes_by_type, content_type)
            if self.create_relationship_csv_file(Rel.HAS_COMMAND):
                session.write_transaction(self.import_has_command_relationships)
            for rel in Rel:
                if rel == Rel.HAS_COMMAND:
                    continue
                if self.create_relationship_csv_file(rel):
                    if rel == Rel.EXECUTES:
                        session.write_transaction(self.import_executes_relationships)
                    else:
                        session.write_transaction(self.import_relationships_by_type, rel)

        after_creating_nodes = datetime.now()
        print(f'Time to create graph: {(after_creating_nodes - before_creating_nodes).total_seconds() / 60} minutes')
        print(f'Time since started: {(after_creating_nodes - self.start_time).total_seconds() / 60} minutes')

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.driver.close()


def create_content_graph() -> None:
    # first we need to remove the neo4j existing data folder
    docker_client = docker.from_env()
    try:
        docker_client.containers.get('neo4j-content').remove(force=True)
    except Exception as e:
        logger.info(f'Could not remove neo4j container: {e}')
    # then we need to create a new one
    shutil.rmtree(REPO_PATH / 'neo4j' / 'data', ignore_errors=True)
    shutil.rmtree(REPO_PATH / 'neo4j' / 'import', ignore_errors=True)
    run_command_os('docker-compose up -d', REPO_PATH / 'neo4j')
    time.sleep(10)  # wait for neo4j to start, TODO - create health check
    with Neo4jContentGraph(REPO_PATH, DATABASE_URL, USERNAME, PASSWORD) as content_graph:
        content_graph.parse_repository()
        content_graph.dump()
    run_command_os('docker-compose down', REPO_PATH / 'neo4j')
