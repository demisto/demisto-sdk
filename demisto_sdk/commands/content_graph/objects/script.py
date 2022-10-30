from pathlib import Path
from typing import List, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.integration_script import \
    IntegrationScript


class Script(IntegrationScript, content_type=ContentType.SCRIPT):  # type: ignore[call-arg]
    tags: List[str]
    is_test: bool

    def metadata_fields(self) -> Set[str]:
        return {"name", "description", "tags"}

    def dump(self, dir: Path, marketplace: MarketplaceVersions) -> None:
        if self.is_test:
            return
        return super().dump(dir, marketplace)
