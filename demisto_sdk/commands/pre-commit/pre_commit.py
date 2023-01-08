from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Union
from demisto_sdk.commands.common.constants import INTEGRATIONS_DIR, SCRIPTS_DIR
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript

@dataclass
class PreCommit:
    integrations_scripts_new: Set[Path]
    integrations_scripts_modified: Set[Path]
    other_files: Set[Path]
        
    def run():
        pass

def main():
    # Get all changed integrations and scripts
    git_util = GitUtil()
    prev_ver = 'origin/master'
    added_files = git_util.added_files(prev_ver=prev_ver)
    modified_files = git_util.modified_files(prev_ver=prev_ver)
    integrations_scripts_added = {file for file in added_files if INTEGRATIONS_DIR in file.parts or SCRIPTS_DIR in file.parts}
    integrations_scripts_modified = {file for file in modified_files if INTEGRATIONS_DIR in file.parts or SCRIPTS_DIR in file.parts}
    other_files = [file for file in added_files + modified_files if file not in integrations_scripts_added | integrations_scripts_modified]
    PreCommit(integrations_scripts_added, integrations_scripts_modified, other_files).run()
        