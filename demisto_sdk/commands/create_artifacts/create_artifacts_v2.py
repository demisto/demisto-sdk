import shutil
from pathlib import Path

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import REPO_PATH
from demisto_sdk.commands.content_graph.content_graph_commands import \
    marshal_content_graph
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import \
    Neo4jContentGraphInterface
from demisto_sdk.commands.content_graph.objects.repository import Repository
from demisto_sdk.commands.find_dependencies.find_dependencies_v2 import PackDependencies


class ContentArtifactManager:

    def __init__(self,
                 marketplace: MarketplaceVersions,
                 output: Path,
                 zip: bool,
                 dependencies: bool,
                 ) -> None:
        self.marketplace = marketplace
        if not output:
            output = REPO_PATH / 'artifacts'
        self.output: Path = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.zip = zip
        self.dependencies = dependencies

    def create_artifacts(self) -> None:
        # TODO add dependencies to marshal when it's fixed
        with Neo4jContentGraphInterface() as content_graph_interface:
            repo: Repository = marshal_content_graph(
                content_graph_interface,
                marketplace=self.marketplace,
            )
            if self.dependencies:
                PackDependencies(
                    content_graph_interface,
                    self.marketplace,
                    self.output / 'packs_dependencies.json', repo
                ).run()

        repo.dump(self.output / 'content_packs', self.marketplace, self.zip)
