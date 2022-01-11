
import logging
import copy
from sys import modules
from docker.models.images import Image
import git
import re
from contextlib import contextmanager
from shutil import rmtree
import requests

from ruamel.yaml import YAML
import urllib3
from wcmatch.pathlib import NEGATE, Path
from typing import Any, Dict, List, Optional, Tuple

from demisto_sdk.commands.common.tools import get_all_docker_images
from demisto_sdk.commands.lint.helpers import add_tmp_lint_files, get_python_version_from_image
from demisto_sdk.commands.common.constants import (TYPE_PWSH, TYPE_PYTHON,
                                                   DemistoException)


logger = logging.getLogger('demisto-sdk')


class LintFilesInfoHelper:

    def __init__(self, ontent_repo: git.Repo, modules: Dict[Path, bytes]) -> None:
        self._mandatory_per_pack = {}
        self._lint_files_per_pack = {}
        self._content_repo = ontent_repo
        self._mandatory_modules = modules
        self._mandatory_files_per_type = {TYPE_PYTHON: {module for module in modules if module.exists() and module.suffix == '.py'},
                                          TYPE_PWSH: {module for module in modules if module.suffix == '.ps1'}}

    def get_lint_files_for_pack(self, pack_path: Path, pack_type):

        lint_files: List[Path] = self._lint_files_per_pack.get(pack_path.name)
        if lint_files is None:

            if pack_type == TYPE_PYTHON:
                lint_files = set(pack_path.glob(["*.py", "!__init__.py", "!_test.py" "!*.tmp"], flags=NEGATE))

            # Facts for Powershell pack
            else:
                lint_files = set(pack_path.glob(["*.ps1", "!*Tests.ps1", "CommonServerPowerShell.ps1", "demistomock.ps1'"],
                                                flags=NEGATE))

            # Add CommonServer to the lint checks
            if 'commonserver' in pack_path.name.lower():

                # Powershell
                if pack_type == TYPE_PWSH:
                    lint_files = {pack_path / 'CommonServerPowerShell.ps1'}
                # Python
                elif pack_type == TYPE_PYTHON:
                    lint_files = {pack_path / 'CommonServerPython.py'}
            else:
                mandatory_modules = self._mandatory_files_per_type[pack_type]
                test_modules = {pack_path / module.name for module in mandatory_modules}
                lint_files = lint_files.difference(test_modules)

            # Remove files that are in gitignore
            log_prompt = f'Pack {pack_path.name}'
            if lint_files:
                lint_files_list = copy.deepcopy(lint_files)
                for lint_file in lint_files_list:
                    if lint_file.name.startswith('test_') or lint_file.name.endswith('_test.py'):
                        lint_files.remove(lint_file)

                files_to_ignore = set(self._content_repo.ignored(lint_files))
                for file in files_to_ignore:
                    logger.info(f"{log_prompt} - Skipping gitignore file {file}")
                    lint_files.remove(file)

                for lint_file in lint_files:
                    logger.info(f"{log_prompt} - Lint file {lint_file}")
            else:
                logger.info(f"{log_prompt} - Lint files not found")

            self._lint_files_per_pack[pack_path.name] = lint_files

        return lint_files

    def get_mandatory_files_for_pack(self, pack_path: Path, pack_type: str):

        lint_files: List[Path] = self.get_lint_files_for_pack(pack_path=pack_path, pack_type=pack_type)
        mandatory_files: List[Path] = self._mandatory_per_pack.get(pack_path.name)
        if mandatory_files is None:
            mandatory_files = []
            try:

                if pack_type == TYPE_PYTHON:
                    # Append empty so it will exists
                    cur_path = pack_path / "CommonServerUserPython.py"
                    mandatory_files.append(cur_path)
                    if not cur_path.exists():
                        cur_path.touch()

                    mandatory_files.extend(self.get_requiered_api_modules(lint_files))

                if mandatory_files:
                    self._mandatory_per_pack[pack_path.name] = mandatory_files

            except Exception as e:
                logger.error(f'can not add mandatory files for pack {pack_path}: {str(e)}')

        # Add mandatory test,lint modules
        mandatory_files.extend(self._mandatory_files_per_type.get(pack_type, []))
        return mandatory_files

    def get_requiered_api_modules(self, lint_files):
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
