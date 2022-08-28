from pathlib import Path
import shutil
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import REPO_PATH
from demisto_sdk.commands.content_graph.content_graph_commands import (create_content_graph,
                                                                       load_content_graph,
                                                                       marshal_content_graph,
                                                                       )
from demisto_sdk.commands.content_graph.objects.repository import Repository


class ContentArtifactManager:

    def __init__(self,
                 marketplace: MarketplaceVersions,
                 output: Path) -> None:
        self.marketplace = marketplace
        if not output:
            output = REPO_PATH / 'artifacts' / marketplace.value
        self.output = output
        
    def create_artifacts(self) -> None:
        # TODO add dependencies to marshal when it's fixed
        repo: Repository = marshal_content_graph(marketplace=self.marketplace,
                                                 with_dependencies=False)
        shutil.rmtree(self.output, ignore_errors=True)
        repo.dump(self.output, self.marketplace)
