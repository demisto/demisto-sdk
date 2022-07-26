import multiprocessing
import neo4j
import pickle

from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple, Iterator, Dict

from constants import PACKS_FOLDER, ContentTypes, Rel
from parsers.pack import PackSubGraphCreator

DATABASE_URL = 'bolt://localhost:7687'
USERNAME = 'dtavori'
PASSWORD = 'Aa123456'
REPO_PATH = Path('/Users/dtavori/dev/demisto/content/')
BATCH_SIZE = 10000


def load_pickle(url: str) -> Any:
    try:
        with open(url, 'rb') as file:
            return pickle.load(file)
    except Exception:
        return []


def dump_pickle(url: str, data: Any) -> None:
    with open(url, 'wb') as file:
        file.write(pickle.dumps(data))


def batches_of(l: List[Any], size: int = BATCH_SIZE):
    return (l[pos:pos + size] for pos in range(0, len(l), size))


class ContentGraph:
    def __init__(self, repo_path: Path, database_uri: str, user: str = None, password: str = None) -> None:
        self.start_time = datetime.now()
        self.end_time = None
        self.packs_path: Path = repo_path / PACKS_FOLDER
        auth: Optional[Tuple[str]] = (user, password) if user and password else None
        self.driver: neo4j.Neo4jDriver = neo4j.GraphDatabase.driver(database_uri, auth=auth)
        self.nodes: List[Dict[str, Any]] = load_pickle('/Users/dtavori/dev/demisto/content-graph/nodes.pkl')
        self.relationships: List[Dict[str, Any]] = load_pickle('/Users/dtavori/dev/demisto/content-graph/rels.pkl')
    
    def __enter__(self):
        with self.driver.session() as session:
            tx = session.begin_transaction()
            self.create_constraints(tx)
            self.create_indexes(tx)
            tx.commit()
            tx.close()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        dump_pickle('/Users/dtavori/dev/demisto/content-graph/nodes.pkl', self.nodes)
        dump_pickle('/Users/dtavori/dev/demisto/content-graph/rels.pkl', self.relationships)
        before_creating_nodes = datetime.now()
        print(f'Time since started: {(before_creating_nodes - self.start_time).total_seconds() / 60} minutes')
        self.make_nodes_transaction()
        after_creating_nodes = datetime.now()
        print(f'Time to create nodes: {(after_creating_nodes - before_creating_nodes).total_seconds() / 60} minutes')
        print(f'Time since started: {(after_creating_nodes - self.start_time).total_seconds() / 60} minutes')
        before_creating_rels = datetime.now()
        self.make_relationships_transaction()
        after_creating_rels = datetime.now()
        print(f'Time to create rels: {(after_creating_rels - before_creating_rels).total_seconds() / 60} minutes')
        print(f'Time since started: {(after_creating_rels - self.start_time).total_seconds() / 60} minutes')
        self.driver.close()
    
    def iter_packs(self) -> Iterator[Path]:
        for path in self.packs_path.iterdir():
            if path.is_dir():
                yield path
    
    def parse_repository(self) -> None:
        repo_packs: Iterator[Path] = self.iter_packs()
        return self.parse_packs(repo_packs)
    
    def parse_packs(self, packs_paths: Iterator[Path]) -> None:
        """ Parses packs into nodes and relationships by given paths. """
        if self.nodes and self.relationships:
            print('Skipping parsing.')
            return
        pool = multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1)
        for pack_nodes, pack_relationships in pool.map(PackSubGraphCreator.from_path, packs_paths):
            self.nodes.extend(pack_nodes)
            self.relationships.extend(pack_relationships)


    @staticmethod
    def create_indexes(tx: neo4j.Transaction) -> None:
        queries = [
            f'CREATE INDEX node_id IF NOT EXISTS FOR (n:{ContentTypes.BASE_CONTENT}) ON (n.node_id)',
        ]
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

    @staticmethod
    def create_constraints(tx: neo4j.Transaction) -> None:
        queries: List[str] = []
        queries.extend(ContentGraph.build_nodes_props_uniqueness_queries())
        queries.extend(ContentGraph.build_nodes_props_existence_queries())
        queries.extend(ContentGraph.build_relationships_props_existence_queries())
        for query in queries:
            print(query)
            tx.run(query)

    @staticmethod
    def merge_nodes_batch(tx: neo4j.Transaction, batch: List[Dict[str, Any]]) -> None:
        print('In merge_nodes_batch()')
        query = (
            'UNWIND $batch as row '
            'CALL apoc.merge.node(row.labels, row.data) yield node '
            'RETURN count(*) AS count_of_nodes'
        )
        result = tx.run(query, batch=batch).single()
        print(result['count_of_nodes'])

    @staticmethod
    def merge_relationships_batch(tx: neo4j.Transaction, batch: List[Dict[str, Any]]) -> None:
        print('In merge_relationships_batch()')
        query = (
            'UNWIND $batch as row '
            f'MATCH (m:{ContentTypes.BASE_CONTENT}{{id: row.from}}) '
            f'MERGE (n:{ContentTypes.BASE_CONTENT}{{id: row.to}}) '
            'WITH row, n, m '
            'CALL apoc.merge.relationship(m, row.type, {}, row.props, n) '
            'yield rel '
            'RETURN count(*) AS count_of_rels'
        )
        result = tx.run(query, batch=batch).single()
        print(result['count_of_rels'])

    def make_nodes_transaction(self) -> None:
        with self.driver.session() as session:
            for batch in batches_of(self.nodes):
                session.write_transaction(self.merge_nodes_batch, batch)

    def make_relationships_transaction(self) -> None:
        with self.driver.session() as session:
            for batch in batches_of(self.relationships):
                session.write_transaction(self.merge_relationships_batch, batch)


def main() -> None:
    print(f'Starting...')
    with ContentGraph(REPO_PATH, DATABASE_URL, USERNAME, PASSWORD) as content_graph:
        content_graph.parse_repository()
    

if __name__ == '__main__':
    main()
