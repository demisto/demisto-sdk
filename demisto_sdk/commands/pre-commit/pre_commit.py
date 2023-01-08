from dataclasses import dataclass
from pathlib import Path
from typing import List, Union
from demisto_sdk.commands.common.constants import INTEGRATIONS_DIR, SCRIPTS_DIR
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript

@dataclass
class PreCommit:
    integrations_scripts_new: List[Path]
    integrations_scripts_modified: List[Path]
    other_files: List[Path]
    
    def __post_init__(self):
        self.integrations_scripts_new = []
        self.integrations_scripts_modified = []
        self.other_files = []
    
    def run():

def main():
    # Get all changed integrations and scripts
    git_util = GitUtil()
    prev_ver = 'origin/master'
    added_files = git_util.added_files(prev_ver=prev_ver)
    modified_files = git_util.modified_files(prev_ver=prev_ver)
    integrations_scripts_new = {file for file in added_files if INTEGRATIONS_DIR in file.parts or SCRIPTS_DIR in file.parts}
    integrations_scripts_modified = {file for file in modified_files if INTEGRATIONS_DIR in file.parts or SCRIPTS_DIR in file.parts}
    other_files = [file for file in added_files + modified_files if file not in integrations_scripts_new | integrations_scripts_modified]
    changed_file_paths = GitUtil()
    content_items: List[IntegrationScript] = [BaseContent.from_path(path) for path in changed_file_paths]  # type: ignore[misc]
    for content_item in content_items:
        docker_image = content_item.docker_image
        