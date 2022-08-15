
from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes
import demisto_sdk.commands.content_graph.objects.content_item as content_item


class TestPlaybookParser(content_item.PlaybookParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        # super().__init__(path, pack_marketplaces, is_test_playbook = True)
        raise content_item.NotAContentItem  # skipping test playbook parsing

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.TEST_PLAYBOOK
