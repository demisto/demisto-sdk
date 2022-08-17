import multiprocessing
from pathlib import Path
from repository import RepositoryParser
from demisto_sdk.commands.content_graph.objects.repository import Repository


class ParserManager:

    def __init__(self, repo_path: Path):
        self.repository_parser: RepositoryParser = RepositoryParser(repo_path)
        self.repository = Repository.from_orm(self.repository_parser)

        for pack in self.repository.packs:
            self.extend_graph_nodes_and_relationships(pack.content_items, pack.relationships)
        self.nodes = ...
        self.relationships = ...
