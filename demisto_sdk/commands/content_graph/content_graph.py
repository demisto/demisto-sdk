import csv
import multiprocessing
import shutil
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

DATABASE_URL = 'bolt://127.0.0.1:7687'
USERNAME = 'neo4j'
PASSWORD = 'test'
REPO_PATH = Path(GitUtil(Content.git()).git_path())
BATCH_SIZE = 10000
IMPORT_PATH = ''  # todo

import logging
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


class ContentGraph:
    def __init__(self, repo_path: Path, database_uri: str, user: str = None, password: str = None) -> None:
        self.start_time = datetime.now()
        self.end_time = None
        self.packs_path: Path = repo_path / PACKS_FOLDER
        auth: Optional[Tuple[str]] = (user, password) if user and password else None
        self.driver: neo4j.Neo4jDriver = neo4j.GraphDatabase.driver(database_uri, auth=auth)
        self.nodes: Dict[ContentTypes, List[Dict[str, Any]]] = load_pickle('/Users/dtavori/dev/demisto/content-graph/nodes.pkl')
        self.relationships: Dict[Rel, List[Dict[str, Any]]] = load_pickle('/Users/dtavori/dev/demisto/content-graph/rels.pkl')
    
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
            print('Container does not exist')

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
            print('Container does not exist')
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
        queries.extend(ContentGraph.build_nodes_props_uniqueness_queries())
        # queries.extend(ContentGraph.build_nodes_props_existence_queries())
        # queries.extend(ContentGraph.build_relationships_props_existence_queries())
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

    def parse_repository(self) -> None:
        """ Parses packs into nodes and relationships by given paths. """
        if self.nodes and self.relationships:
            print('Skipping parsing.')
            return
        pool = multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1)
        for pack_nodes, pack_relationships in pool.map(PackSubGraphCreator.from_path, self.iter_packs()):
            self.extend_graph_nodes_and_relationships(pack_nodes, pack_relationships)

    def iter_packs(self) -> Iterator[Path]:
        for path in self.packs_path.iterdir():  # todo: handle repo path is invalid
            if path.is_dir():
                yield path
    
    def extend_graph_nodes_and_relationships(
        self,
        pack_nodes: Dict[ContentTypes, List[Dict[str, Any]]],
        pack_relationships: Dict[ContentTypes, List[Dict[str, Any]]],
    ) -> None:
        for content_type in ContentTypes:
            if content_type not in self.nodes:
                self.nodes[content_type] = []
            self.nodes[content_type].extend(pack_nodes.get(content_type, []))
        for rel in Rel:
            if rel not in self.relationships:
                self.relationships[rel] = []
            self.relationships[rel].extend(pack_relationships.get(rel, []))

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

    def import_csv_nodes_and_relationships(self) -> None:
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

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        dump_pickle('/Users/dtavori/dev/demisto/content-graph/nodes.pkl', self.nodes)
        dump_pickle('/Users/dtavori/dev/demisto/content-graph/rels.pkl', self.relationships)
        before_creating_nodes = datetime.now()
        print(f'Time since started: {(before_creating_nodes - self.start_time).total_seconds() / 60} minutes')
        self.import_csv_nodes_and_relationships()
        after_creating_nodes = datetime.now()
        print(f'Time to create graph: {(after_creating_nodes - before_creating_nodes).total_seconds() / 60} minutes')
        print(f'Time since started: {(after_creating_nodes - self.start_time).total_seconds() / 60} minutes')
        self.driver.close()

def create_content_graph() -> None:
    shutil.rmtree(REPO_PATH / 'neo4j' / 'data', ignore_errors=True)
    with ContentGraph(REPO_PATH, DATABASE_URL, USERNAME, PASSWORD) as content_graph:
        content_graph.parse_repository()
