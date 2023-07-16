from typing import List, Optional, Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import CONTRIBUTORS_README_TEMPLATE, FileType
from demisto_sdk.commands.common.content.objects.abstract_objects import TextObject
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_mp_tag_parser

json = JSON_Handler()


class Readme(TextObject):
    def __init__(self, path: Union[Path, str]):
        self._path = path
        self.contributors = None
        super().__init__(path)

    def type(self):
        return FileType.README

    @staticmethod
    def prepare_contributors_text(contrib_list):
        fixed_contributor_names = [
            f" - {contrib_name}\n" for contrib_name in contrib_list
        ]
        return CONTRIBUTORS_README_TEMPLATE.format(
            contributors_names="".join(fixed_contributor_names)
        )

    def mention_contributors_in_readme(self):
        """Mention contributors in pack readme"""
        try:
            if self.contributors:
                with open(self.contributors.path) as contributors_file:
                    contributor_list = json.load(contributors_file)
                contribution_data = self.prepare_contributors_text(contributor_list)
                with open(self._path, "a+") as readme_file:
                    readme_file.write(contribution_data)
        except Exception as e:
            logger.error(e)

    def handle_marketplace_tags(self):
        """Remove marketplace tags depending on marketplace version"""
        try:
            with open(self._path, "r+") as f:
                text = f.read()
                parsed_text = get_mp_tag_parser().parse_text(text)
                if len(text) != len(parsed_text):
                    f.seek(0)
                    f.write(parsed_text)
                    f.truncate()
        except Exception as e:
            logger.error(e)

    def dump(self, dest_dir: Optional[Union[Path, str]] = None) -> List[Path]:
        self.mention_contributors_in_readme()
        self.handle_marketplace_tags()
        return super().dump(dest_dir)
