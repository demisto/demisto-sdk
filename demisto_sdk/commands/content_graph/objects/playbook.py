from pathlib import Path
from typing import Dict

from demisto_sdk.commands.common.constants import (
    PACKS_README_FILE_NAME,
    TEST_PLAYBOOKS_DIR,
    RelatedFileType,
)
from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_playbook import BasePlaybook


class Playbook(BasePlaybook, content_type=ContentType.PLAYBOOK):  # type: ignore[call-arg]
    is_test: bool = False

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "tasks" in _dict:
            if TEST_PLAYBOOKS_DIR not in path.parts and path.suffix == ".yml":
                return True
        return False

    @property
    def readme(self) -> str:
        return get_file(
            str(self.path.parent / PACKS_README_FILE_NAME),
            return_content=True,
            git_sha=self.git_sha,
        )

    def get_related_content(self) -> Dict[RelatedFileType, dict]:
        related_content_ls = super().get_related_content()
        related_content_ls.update(
            {
                RelatedFileType.IMAGE: {
                    "path": self.path.parents[1]
                    / "doc_files"
                    / str(self.path.parts[-1])
                    .replace(".yml", ".png")
                    .replace("playbook-", ""),
                    "git_status": None,
                },
                RelatedFileType.README: {
                    "path": self.path.parent
                    / str(self.path.parts[-1]).replace(
                        ".yml", f"_{PACKS_README_FILE_NAME}"
                    ),
                    "git_status": None,
                },
            }
        )
        return related_content_ls
