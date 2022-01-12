
import copy
import logging
import re
from contextlib import contextmanager
from shutil import rmtree
from sys import modules
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import git
import requests
import urllib3
from demisto_sdk.commands.common.constants import (TYPE_PWSH, TYPE_PYTHON,
                                                   DemistoException)
from demisto_sdk.commands.common.tools import get_all_docker_images
from demisto_sdk.commands.lint.helpers import (add_tmp_lint_files,
                                               get_python_version_from_image, is_lint_available_for_pack_type)
from docker.models.images import Image
from ruamel.yaml import YAML
from wcmatch.pathlib import NEGATE, EXTGLOB, Path

logger = logging.getLogger('demisto-sdk')

PACK_GLOB_FILES_PATTERNS = {
    TYPE_PYTHON: "!(__init__|*_test|test_*).py",
    TYPE_PWSH: "!(*.Tests).ps1"
}
class LintFilesInfoHelper:

    def __init__(self, ontent_repo: git.Repo, mandatory_modules: Dict[Path, bytes]) -> None:
        self._mandatory_per_pack = {}
        self._lint_files_per_pack = {}
        self._content_repo = ontent_repo

        self._mandatory_files_per_type = {TYPE_PYTHON: {module for module in mandatory_modules if module.exists() and module.suffix == '.py'},
                                          TYPE_PWSH: {module for module in mandatory_modules if module.suffix == '.ps1'}}

    def get_lint_files_for_pack(self, pack_path: Path, pack_type: str):

        log_prompt = f'Pack {pack_path.name}'
        
        if not is_lint_available_for_pack_type(pack_type):
            logger.info(f'{log_prompt} - No lint files available due to not Python, Powershell package - Pack is {pack_type}')
            return None
        
        lint_files: List[Path] = self._lint_files_per_pack.get(pack_path.name)
        if lint_files is None:

            glob_patterns = PACK_GLOB_FILES_PATTERNS[pack_type]
            lint_files = set(pack_path.glob(glob_patterns, flags=NEGATE|EXTGLOB))

            # Add CommonServer to the lint checks
            if 'commonserver' in pack_path.name.lower():
                common_server_file = 'CommonServerPython.py' if pack_type == TYPE_PYTHON else 'CommonServerPowerShell.ps1'
                lint_files = {pack_path / common_server_file}
            else:
                mandatory_modules = self._mandatory_files_per_type[pack_type]
                test_modules = {pack_path / module.name for module in mandatory_modules}
                lint_files = lint_files.difference(test_modules)

            # Remove files that are in gitignore
            
            if lint_files:
                files_to_ignore = set(self._content_repo.ignored(lint_files))
                for file in files_to_ignore:
                    logger.info(f"{log_prompt} - Skipping gitignore file {file}")
                    lint_files.remove(file)
            else:
                logger.info(f"{log_prompt} - Lint files not found")

            self._lint_files_per_pack[pack_path.name] = lint_files
        return lint_files

    def get_mandatory_files_for_pack(self, pack_path: Path, pack_type: str):

        lint_files: List[Path] = self.get_lint_files_for_pack(pack_path=pack_path, pack_type=pack_type)
        mandatory_files: set[Path] = self._mandatory_per_pack.get(pack_path.name)
        if mandatory_files is None:
            mandatory_files = set()
            try:

                if pack_type == TYPE_PYTHON:
                    # Append empty so it will exists
                    cur_path = pack_path / "CommonServerUserPython.py"
                    mandatory_files.add(cur_path)
                    if not cur_path.exists():
                        cur_path.touch()

                    mandatory_files.update(self._get_requiered_api_modules(lint_files))

                self._mandatory_per_pack[pack_path.name] = mandatory_files

            except Exception as e:
                logger.error(f'can not add mandatory files for pack {pack_path}: {str(e)}')

        # Add mandatory test,lint modules
        mandatory_files.update(self._mandatory_files_per_type.get(pack_type, []))
        return mandatory_files

    def _get_requiered_api_modules(self, lint_files):
        # Get the API modules if needed
        results = set()
        module_regex = r'from ([\w\d]+ApiModule) import \*(?:  # noqa: E402)?'
        for lint_file in lint_files:
            module_name = ""
            data = lint_file.read_text()
            module_match = re.search(module_regex, data)
            if module_match:
                module_name = module_match.group(1)
                rel_api_path = Path('Packs/ApiModules/Scripts') / module_name / f'{module_name}.py'
                results.add(Path(self._content_repo.working_dir) / rel_api_path)
                # mandatory_files.append(Path(self._content_repo.working_dir) / rel_api_path)
        
        return results
