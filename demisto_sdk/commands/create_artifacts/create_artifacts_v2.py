from pathlib import Path
import shutil
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import REPO_PATH
from demisto_sdk.commands.content_graph.content_graph_commands import (
    marshal_content_graph,
)
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import Neo4jContentGraphInterface
from demisto_sdk.commands.content_graph.objects.repository import Repository


class ContentArtifactManager:

    def __init__(self,
                 marketplace: MarketplaceVersions,
                 output: Path,
                 no_zip: bool) -> None:
        self.marketplace = marketplace
        if not output:
            output = REPO_PATH / 'artifacts'
        self.output: Path = output / marketplace.value / 'content-packs'
        self.output.mkdir(parents=True, exist_ok=True)
        self.no_zip = no_zip

    def create_artifacts(self) -> None:
        # TODO add dependencies to marshal when it's fixed
        with Neo4jContentGraphInterface() as content_graph_interface:
            repo: Repository = marshal_content_graph(
                content_graph_interface,
                marketplace=self.marketplace,
            )
        shutil.rmtree(self.output, ignore_errors=True)
        repo.dump(self.output, self.marketplace, self.no_zip)
