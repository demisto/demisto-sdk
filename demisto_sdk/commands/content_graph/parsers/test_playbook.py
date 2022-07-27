
from pathlib import Path
from typing import List

from constants import ContentTypes
from .content_item import NotAContentItem
from .playbook import PlaybookParser


class TestPlaybookParser(PlaybookParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        # super().__init__(path, pack_marketplaces, is_test_playbook = True)
        raise NotAContentItem  # skipping test playbook parsing

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.TEST_PLAYBOOK

    # def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
    #     raise NotAContentItem
    #     # super().__init__(path, pack_marketplaces)
