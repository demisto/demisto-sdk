# STD packages
import concurrent.futures
import json
import logging
import os
import re
import sys
import textwrap
from typing import Any, Dict, List, Set

# Third party packages
import docker
import docker.errors
import git
import requests.exceptions
import urllib3.exceptions
from wcmatch.pathlib import Path, PosixPath

from demisto_sdk.commands.common.constants import (PACKS_PACK_META_FILE_NAME,
                                                   TYPE_PWSH, TYPE_PYTHON,
                                                   DemistoException)
# Local packages
from demisto_sdk.commands.common.logger import Colors
from demisto_sdk.commands.common.tools import (find_file, find_type,
                                               get_content_path,
                                               get_file_displayed_name,
                                               get_json,
                                               is_external_repository,
                                               pack_name_to_posix_path,
                                               print_error, print_v,
                                               print_warning,
                                               retrieve_file_ending,
                                               get_parent_directory_name)
from demisto_sdk.commands.find_dependencies.find_dependencies import get_packs_dependent_on_given_packs
from demisto_sdk.commands.lint.helpers import (EXIT_CODES, FAIL, PWSH_CHECKS,
                                               PY_CHCEKS,
                                               build_skipped_exit_code,
                                               generate_coverage_report,
                                               get_test_modules, validate_env)
from demisto_sdk.commands.lint.linter import Linter
from demisto_sdk.commands.common.git_util import GitUtil
logger = logging.getLogger('demisto-sdk')
sha1Regex = re.compile(r'\b[0-9a-fA-F]{40}\b', re.M)


class LintManager:
    """ LintManager used to activate lint command using Linters in a single or multi thread.

    Attributes:
        input(str): Directories to run lint on.
        git(bool): Perform lint and test only on chaged packs.
        all_packs(bool): Whether to run on all packages.
        verbose(int): Whether to output a detailed response.
        quiet(bool): Whether to output a quiet response.
        log_path(str): Path to all levels of logs.
        prev_ver(str): Previous branch or SHA1 commit to run checks against.
        json_file_path(str): Path to a json file to write the run resutls to.
        id_set_path(str): Path to an existing id_set.json.
        check_dependent_packs(bool): Whether to run lint also on the packs dependent on the given packs.
    """

    def __init__(self, input: str, git: bool, all_packs: bool, quiet: bool, verbose: int, prev_ver: str,
                 json_file_path: str = '', id_set_path: str = None, check_dependent_packs: bool = False):

        # Verbosity level
        self._verbose = not quiet if quiet else verbose
        # Gather facts for manager
        self._facts: dict = self._gather_facts()
        self._prev_ver = prev_ver
        self._all_packs = all_packs
        # Set 'git' to true if no packs have been specified, 'lint' should operate as 'lint -g'
        lint_no_packs_command = not git and not all_packs and not input
        if lint_no_packs_command:
            git = True
        # Filter packages to lint and test check
        self._pkgs: List[PosixPath] = self._get_packages(content_repo=self._facts["content_repo"],
                                                    input=input,
                                                    git=git,
                                                    all_packs=all_packs,
                                                    base_branch=self._prev_ver)
        self._id_set_path = id_set_path
        self._check_dependent_packs = check_dependent_packs
        if self._check_dependent_packs:
            print("Checking for dependent packs...")
            dependent = [pack_name_to_posix_path(pack) for pack in
                         get_packs_dependent_on_given_packs(self._pkgs, self._id_set_path)]
            self._pkgs = list(set(self._pkgs + dependent))  # remove dups
            if dependent:
                print(f"Found {Colors.Fg.cyan}{len(dependent)}{Colors.reset} dependent packages. Executing lint and "
                      f"test on dependent packages as well.")

        if json_file_path:
            if os.path.isdir(json_file_path):
                json_file_path = os.path.join(json_file_path, 'lint_outputs.json')
        self.json_file_path = json_file_path
        self.linters_error_list: list = []

    @staticmethod
    def _gather_facts() -> Dict[str, Any]:
        """ Gather shared required facts for lint command execution - Also perform mandatory resource checkup.
            1. Content repo object.
            2. Requirements file for docker images.
            3. Mandatory test modules - demisto-mock.py etc
            3. Docker daemon check.

        Returns:
            dict: facts
        """
        global logger
        facts = {
            "content_repo": None,
            "requirements_3": None,
            "requirements_2": None,
            "test_modules": None,
            "docker_engine": True
        }
        # Check env requirements satisfied - bootstrap in use
        validate_env()
        # Get content repo object
        is_external_repo = False
        try:
            git_repo = git.Repo(os.getcwd(),
                                search_parent_directories=True)
            remote_url = git_repo.remote().urls.__next__()
            is_fork_repo = 'content' in remote_url
            is_external_repo = is_external_repository()

            if not is_fork_repo and not is_external_repo:
                raise git.InvalidGitRepositoryError

            facts["content_repo"] = git_repo
            logger.debug(f"Content path {git_repo.working_dir}")
        except (git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
            print_warning("You are running demisto-sdk lint not in content repository!")
            logger.warning(f"can't locate content repo {e}")
        # Get global requirements file
        pipfile_dir = Path(__file__).parent / 'resources'
        try:
            for py_num in ['2', '3']:
                pipfile_lock_path = pipfile_dir / f'pipfile_python{py_num}/Pipfile.lock'
                with open(file=pipfile_lock_path) as f:
                    lock_file: dict = json.load(fp=f)["develop"]
                    facts[f"requirements_{py_num}"] = [key + value["version"] for key, value in  # type: ignore
                                                       lock_file.items()]
                    logger.debug(f"Test requirements successfully collected for python {py_num}:\n"
                                 f" {facts[f'requirements_{py_num}']}")
        except (json.JSONDecodeError, IOError, FileNotFoundError, KeyError) as e:
            print_error("Can't parse pipfile.lock - Aborting!")
            logger.critical(f"demisto-sdk-can't parse pipfile.lock {e}")
            sys.exit(1)
        # ￿Get mandatory modulestest modules and Internet connection for docker usage
        try:
            facts["test_modules"] = get_test_modules(content_repo=facts["content_repo"],  # type: ignore
                                                     is_external_repo=is_external_repo)
            logger.debug("Test mandatory modules successfully collected")
        except (git.GitCommandError, DemistoException) as e:
            if is_external_repo:
                print_error('You are running on an external repo - '
                            'run `.hooks/bootstrap` before running the demisto-sdk lint command\n'
                            'See here for additional information: https://xsoar.pan.dev/docs/concepts/dev-setup')
            else:
                print_error(
                    "Unable to get test-modules demisto-mock.py etc - Aborting! corrupt repository or pull from master")
            logger.error(f"demisto-sdk-unable to get mandatory test-modules demisto-mock.py etc {e}")
            sys.exit(1)
        except (requests.exceptions.ConnectionError, urllib3.exceptions.NewConnectionError) as e:
            print_error("Unable to get mandatory test-modules demisto-mock.py etc - Aborting! (Check your internet "
                        "connection)")
            logger.error(f"demisto-sdk-unable to get mandatory test-modules demisto-mock.py etc {e}")
            sys.exit(1)
        # Validating docker engine connection
        docker_client: docker.DockerClient = docker.from_env()
        try:
            docker_client.ping()
        except (requests.exceptions.ConnectionError, urllib3.exceptions.ProtocolError, docker.errors.APIError) as ex:
            if os.getenv("CI") and os.getenv("CIRCLE_PROJECT_REPONAME") == "content":
                # when running lint in content we fail if docker isn't available for some reason
                raise ValueError("Docker engine not available and we are in content CI env. Can not run lint!!") from ex
            facts["docker_engine"] = False
            print_warning("Can't communicate with Docker daemon - check your docker Engine is ON - Skipping lint, "
                          "test which require docker!")
            logger.info("demisto-sdk-Can't communicate with Docker daemon")
        logger.debug("Docker daemon test passed")
        return facts

    def _get_packages(self, content_repo: git.Repo, input: str, git: bool, all_packs: bool, base_branch: str) \
            -> List[PosixPath]:
        """ Get packages paths to run lint command.

        Args:
            content_repo(git.Repo): Content repository object.
            input(str): dir pack specified as argument.
            git(bool): Perform lint and test only on changed packs.
            all_packs(bool): Whether to run on all packages.
            base_branch (str): Name of the branch or sha1 commit to run the diff on.

        Returns:
            List[PosixPath]: Pkgs to run lint
        """
        pkgs: list
        if all_packs or git:
            pkgs = LintManager._get_all_packages(content_dir=content_repo.working_dir)
        else:  # specific pack as input, -i flag has been used
            pkgs = []
            for item in input.split(','):
                is_pack = os.path.isdir(item) and os.path.exists(os.path.join(item, PACKS_PACK_META_FILE_NAME))
                if is_pack:
                    pkgs.extend(LintManager._get_all_packages(content_dir=item))
                else:
                    pkgs.append(Path(item))

        total_found = len(pkgs)
        if git:
            pkgs = self._filter_changed_packages(content_repo=content_repo, pkgs=pkgs,
                                                 base_branch=base_branch)
            for pkg in pkgs:
                print_v(f"Found changed package {Colors.Fg.cyan}{pkg}{Colors.reset}",
                        log_verbose=self._verbose)
        print(f"Executing lint and test on {Colors.Fg.cyan}{len(pkgs)}/{total_found}{Colors.reset} integrations and scripts")

        return pkgs

    @staticmethod
    def _get_all_packages(content_dir: str) -> List[str]:
        """Gets all integration, script in packages and packs in content repo.

        Returns:
            list: A list of integration, script and beta_integration names.
        """
        # Get packages from main content path
        content_main_pkgs: set = set(Path(content_dir).glob(['Integrations/*/',
                                                             'Scripts/*/', ]))
        # Get packages from packs path
        packs_dir: Path = Path(content_dir) / 'Packs'
        content_packs_pkgs: set = set(packs_dir.glob(['*/Integrations/*/',
                                                      '*/Scripts/*/']))
        all_pkgs = content_packs_pkgs.union(content_main_pkgs)

        return list(all_pkgs)

    @staticmethod

    def _get_packages_from_modified_files(modified_files):
        """
        Out of all modified files, return only the files relevant for linting, which are the packages
        (scripts\integrations) under the pack.
        Args:
            modified_files: A list of paths of files recognized as modified.

        Returns:
            A list of paths of modified packages (scripts/integrations)
        """
        return [path for path in modified_files if 'Scripts' in path.parts or 'Intergations' in path.parts]

    @staticmethod
    def _filter_changed_packages(content_repo: git.Repo, pkgs: List[PosixPath], base_branch: str) -> List[PosixPath]:
        """ Checks which packages had changes in them and should run on Lint.
        The diff is calculated using git, and is done by the following cases:
        - case 1: If the active branch is 'master', the diff is between master and the previous commit.
        - case 2: If the active branch is not master, and no other base branch is specified to comapre to,
         the diff is between the active branch and master.
        - case 3: If the base branch is specified, the diff is between the active branch (master\not master) and the given base branch.

        Args:
            pkgs(List[PosixPath]): pkgs to check
            base_branch (str): Name of the branch or sha1 commit to run the diff on.

        Returns:
            List[PosixPath]: A list of names of packages that should run.
        """

        staged_files = {content_repo.working_dir / Path(item.b_path).parent for item in
                        content_repo.active_branch.commit.tree.diff(None, paths=pkgs)}

        if base_branch == 'master' and content_repo.active_branch.name == 'master':
            # case 1: comparing master against the latest previous commit
            last_common_commit = content_repo.remote().refs.master.commit.parents[0]
            print(f"Comparing {Colors.Fg.cyan}master{Colors.reset} to its {Colors.Fg.cyan}previous commit: "
                  f"{last_common_commit} {Colors.reset}")

        else:
            # cases 2+3: compare the active branch (master\not master) against the given base branch (master\not master)
            if sha1Regex.match(base_branch):  # if the base branch is given as a commit hash
                last_common_commit = base_branch
            else:
                last_common_commit = content_repo.merge_base(content_repo.active_branch.commit,
                                                         f'{content_repo.remote()}/{base_branch}')[0]
            print(f"Comparing {Colors.Fg.cyan}{content_repo.active_branch}{Colors.reset} to"
              f" last common commit with {Colors.Fg.cyan}{last_common_commit}{Colors.reset}")

        changed_from_base = {content_repo.working_dir / Path(item.b_path).parent for item in
                             content_repo.active_branch.commit.tree.diff(last_common_commit, paths=pkgs)}
        all_changed = staged_files.union(changed_from_base)
        pkgs_to_check = all_changed.intersection(pkgs)

        return list(pkgs_to_check)

    def run_dev_packages(self, parallel: int, no_flake8: bool, no_xsoar_linter: bool, no_bandit: bool, no_mypy: bool,
                         no_pylint: bool, no_coverage: bool, coverage_report: str,
                         no_vulture: bool, no_test: bool, no_pwsh_analyze: bool, no_pwsh_test: bool,
                         keep_container: bool,
                         test_xml: str, failure_report: str, docker_timeout: int) -> int:
        """ Runs the Lint command on all given packages.

        Args:
            parallel(int): Whether to run command on multiple threads
            no_flake8(bool): Whether to skip flake8
            no_xsoar_linter(bool): Whether to skip xsoar linter
            no_bandit(bool): Whether to skip bandit
            no_mypy(bool): Whether to skip mypy
            no_vulture(bool): Whether to skip vulture
            no_pylint(bool): Whether to skip pylint
            no_coverage(bool): Run pytest without coverage report
            coverage_report(str): the directory fo exporting the coverage data
            no_test(bool): Whether to skip pytest
            no_pwsh_analyze(bool): Whether to skip powershell code analyzing
            no_pwsh_test(bool): whether to skip powershell tests
            keep_container(bool): Whether to keep the test container
            test_xml(str): Path for saving pytest xml results
            failure_report(str): Path for store failed packs report
            docker_timeout(int): timeout for docker requests

        Returns:
            int: exit code by fail exit codes by var EXIT_CODES
        """
        lint_status: Dict = {
            "fail_packs_flake8": [],
            "fail_packs_XSOAR_linter": [],
            "fail_packs_bandit": [],
            "fail_packs_mypy": [],
            "fail_packs_vulture": [],
            "fail_packs_pylint": [],
            "fail_packs_pytest": [],
            "fail_packs_pwsh_analyze": [],
            "fail_packs_pwsh_test": [],
            "fail_packs_image": [],
            "warning_packs_flake8": [],
            "warning_packs_XSOAR_linter": [],
            "warning_packs_bandit": [],
            "warning_packs_mypy": [],
            "warning_packs_vulture": [],
            "warning_packs_pylint": [],
            "warning_packs_pytest": [],
            "warning_packs_pwsh_analyze": [],
            "warning_packs_pwsh_test": [],
            "warning_packs_image": [],
        }

        # Python or powershell or both
        pkgs_type = []

        # Detailed packages status
        pkgs_status = {}

        # Skiped lint and test codes
        skipped_code = build_skipped_exit_code(no_flake8=no_flake8, no_bandit=no_bandit, no_mypy=no_mypy,
                                               no_vulture=no_vulture, no_xsoar_linter=no_xsoar_linter,
                                               no_pylint=no_pylint, no_test=no_test, no_pwsh_analyze=no_pwsh_analyze,
                                               no_pwsh_test=no_pwsh_test, docker_engine=self._facts["docker_engine"])

        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
            return_exit_code: int = 0
            return_warning_code: int = 0
            results = []
            # Executing lint checks in different threads
            for pack in sorted(self._pkgs):
                linter: Linter = Linter(pack_dir=pack,
                                        content_repo="" if not self._facts["content_repo"] else
                                        Path(self._facts["content_repo"].working_dir),
                                        req_2=self._facts["requirements_2"],
                                        req_3=self._facts["requirements_3"],
                                        docker_engine=self._facts["docker_engine"],
                                        docker_timeout=docker_timeout)
                results.append(executor.submit(linter.run_dev_packages,
                                               no_flake8=no_flake8,
                                               no_bandit=no_bandit,
                                               no_mypy=no_mypy,
                                               no_vulture=no_vulture,
                                               no_xsoar_linter=no_xsoar_linter,
                                               no_pylint=no_pylint,
                                               no_test=no_test,
                                               no_pwsh_analyze=no_pwsh_analyze,
                                               no_pwsh_test=no_pwsh_test,
                                               modules=self._facts["test_modules"],
                                               keep_container=keep_container,
                                               test_xml=test_xml,
                                               no_coverage=no_coverage))
            try:
                for future in concurrent.futures.as_completed(results):
                    pkg_status = future.result()
                    pkgs_status[pkg_status["pkg"]] = pkg_status
                    if pkg_status["exit_code"]:
                        for check, code in EXIT_CODES.items():
                            if pkg_status["exit_code"] & code:
                                lint_status[f"fail_packs_{check}"].append(pkg_status["pkg"])
                        if not return_exit_code & pkg_status["exit_code"]:
                            return_exit_code += pkg_status["exit_code"]
                    if pkg_status["warning_code"]:
                        for check, code in EXIT_CODES.items():
                            if pkg_status["warning_code"] & code:
                                lint_status[f"warning_packs_{check}"].append(pkg_status["pkg"])
                        if not return_warning_code & pkg_status["warning_code"]:
                            return_warning_code += pkg_status["warning_code"]
                    if pkg_status["pack_type"] not in pkgs_type:
                        pkgs_type.append(pkg_status["pack_type"])
            except KeyboardInterrupt:
                print_warning("Stop demisto-sdk lint - Due to 'Ctrl C' signal")
                try:
                    executor.shutdown(wait=False)
                except Exception:
                    pass
                return 1
            except Exception as e:
                print_warning(f"Stop demisto-sdk lint - Due to Exception {e}")
                try:
                    executor.shutdown(wait=False)
                except Exception:
                    pass
                return 1

        self._report_results(lint_status=lint_status,
                             pkgs_status=pkgs_status,
                             return_exit_code=return_exit_code,
                             return_warning_code=return_warning_code,
                             skipped_code=int(skipped_code),
                             pkgs_type=pkgs_type,
                             no_coverage=no_coverage,
                             coverage_report=coverage_report)
        self._create_failed_packs_report(lint_status=lint_status, path=failure_report)

        # check if there were any errors during lint run , if so set to FAIL as some error codes are bigger
        # then 512 and will not cause failure on the exit code.
        if return_exit_code:
            return_exit_code = FAIL
        return return_exit_code

    def _report_results(self, lint_status: dict, pkgs_status: dict, return_exit_code: int, return_warning_code: int,
                        skipped_code: int,
                        pkgs_type: list,
                        no_coverage: bool, coverage_report: str):
        """ Log report to console

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
            return_warning_code(int): warning code will indicate which lint or test caused warning messages
            skipped_code(int): skipped test code
            pkgs_type(list): list determine which pack type exits.
            no_coverage(bool): Do NOT create coverage report.

     """
        self.report_pass_lint_checks(return_exit_code=return_exit_code,
                                     skipped_code=skipped_code,
                                     pkgs_type=pkgs_type)
        self.report_failed_lint_checks(return_exit_code=return_exit_code,
                                       pkgs_status=pkgs_status,
                                       lint_status=lint_status)
        self.report_warning_lint_checks(return_warning_code=return_warning_code,
                                        pkgs_status=pkgs_status,
                                        lint_status=lint_status,
                                        all_packs=self._all_packs)
        self.report_unit_tests(return_exit_code=return_exit_code,
                               pkgs_status=pkgs_status,
                               lint_status=lint_status)
        self.report_failed_image_creation(return_exit_code=return_exit_code,
                                          pkgs_status=pkgs_status,
                                          lint_status=lint_status)
        if not no_coverage:
            if coverage_report:
                generate_coverage_report(html=True, xml=True, cov_dir=coverage_report)
            else:
                generate_coverage_report()

        self.report_summary(pkg=self._pkgs, lint_status=lint_status, all_packs=self._all_packs)
        self.create_json_output()

    @staticmethod
    def report_pass_lint_checks(return_exit_code: int, skipped_code: int, pkgs_type: list):
        """ Log PASS/FAIL on each lint/test

        Args:
            return_exit_code(int): exit code will indicate which lint or test failed
            skipped_code(int): skipped test code.
            pkgs_type(list): list determine which pack type exits.
         """
        longest_check_key = len(max(EXIT_CODES.keys(), key=len))
        for check, code in EXIT_CODES.items():
            spacing = longest_check_key - len(check)
            if 'XSOAR_linter' in check:
                check_str = check.replace('_', ' ')
            else:
                check_str = check.capitalize().replace('_', ' ')
            if (check in PY_CHCEKS and TYPE_PYTHON in pkgs_type) or (check in PWSH_CHECKS and TYPE_PWSH in pkgs_type):
                if code & skipped_code:
                    print(f"{check_str} {' ' * spacing}- {Colors.Fg.cyan}[SKIPPED]{Colors.reset}")
                elif code & return_exit_code:
                    print(f"{check_str} {' ' * spacing}- {Colors.Fg.red}[FAIL]{Colors.reset}")
                else:
                    print(f"{check_str} {' ' * spacing}- {Colors.Fg.green}[PASS]{Colors.reset}")
            elif check != 'image':
                print(f"{check_str} {' ' * spacing}- {Colors.Fg.cyan}[SKIPPED]{Colors.reset}")

    def report_failed_lint_checks(self, lint_status: dict, pkgs_status: dict, return_exit_code: int):
        """ Log failed lint log if exsits

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
        """
        for check in ["flake8", "XSOAR_linter", "bandit", "mypy", "vulture"]:
            if EXIT_CODES[check] & return_exit_code:
                sentence = f" {check.capitalize()} errors "
                print(f"\n{Colors.Fg.red}{'#' * len(sentence)}{Colors.reset}")
                print(f"{Colors.Fg.red}{sentence}{Colors.reset}")
                print(f"{Colors.Fg.red}{'#' * len(sentence)}{Colors.reset}\n")
                for fail_pack in lint_status[f"fail_packs_{check}"]:
                    print(f"{Colors.Fg.red}{pkgs_status[fail_pack]['pkg']}{Colors.reset}")
                    print(pkgs_status[fail_pack][f"{check}_errors"])
                    self.linters_error_list.append({
                        'linter': check,
                        'pack': fail_pack,
                        'type': 'error',
                        'messages': pkgs_status[fail_pack][f"{check}_errors"]
                    })

        for check in ["pylint", "pwsh_analyze", "pwsh_test"]:
            check_str = check.capitalize().replace('_', ' ')
            if EXIT_CODES[check] & return_exit_code:
                sentence = f" {check_str} errors "
                print(f"\n{Colors.Fg.red}{'#' * len(sentence)}{Colors.reset}")
                print(f"{Colors.Fg.red}{sentence}{Colors.reset}")
                print(f"{Colors.Fg.red}{'#' * len(sentence)}{Colors.reset}\n")
                for fail_pack in lint_status[f"fail_packs_{check}"]:
                    print(f"{Colors.Fg.red}{fail_pack}{Colors.reset}")
                    for image in pkgs_status[fail_pack]["images"]:
                        print(image[f"{check}_errors"])

    def report_warning_lint_checks(self, lint_status: dict, pkgs_status: dict, return_warning_code: int,
                                   all_packs: bool):
        """ Log warnings lint log if exists

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_warning_code(int): exit code will indicate which lint or test caused warnings
            all_packs(bool) if all packs runs then no need for warnings messages.
        """
        if not all_packs:
            for check in ["flake8", "XSOAR_linter", "bandit", "mypy", "vulture"]:
                if EXIT_CODES[check] & return_warning_code:
                    sentence = f" {check.capitalize()} warnings "
                    print(f"\n{Colors.Fg.orange}{'#' * len(sentence)}{Colors.reset}")
                    print(f"{Colors.Fg.orange}{sentence}{Colors.reset}")
                    print(f"{Colors.Fg.orange}{'#' * len(sentence)}{Colors.reset}\n")
                    for fail_pack in lint_status[f"warning_packs_{check}"]:
                        print(f"{Colors.Fg.orange}{pkgs_status[fail_pack]['pkg']}{Colors.reset}")
                        print(pkgs_status[fail_pack][f"{check}_warnings"])
                        self.linters_error_list.append({
                            'linter': check,
                            'pack': fail_pack,
                            'type': 'warning',
                            'messages': pkgs_status[fail_pack][f"{check}_warnings"]
                        })

    def report_unit_tests(self, lint_status: dict, pkgs_status: dict, return_exit_code: int):
        """ Log failed unit-tests , if verbosity specified will log also success unit-tests

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
        """
        # Indentation config
        preferred_width = 100
        pack_indent = 2
        pack_prefix = " " * pack_indent + "- Package: "
        wrapper_pack = textwrap.TextWrapper(initial_indent=pack_prefix,
                                            width=preferred_width,
                                            subsequent_indent=' ' * len(pack_prefix))
        docker_indent = 6
        docker_prefix = " " * docker_indent + "- Image: "
        wrapper_docker_image = textwrap.TextWrapper(initial_indent=docker_prefix,
                                                    width=preferred_width,
                                                    subsequent_indent=' ' * len(docker_prefix))
        test_indent = 9
        test_prefix = " " * test_indent + "- "
        wrapper_test = textwrap.TextWrapper(initial_indent=test_prefix, width=preferred_width,
                                            subsequent_indent=' ' * len(test_prefix))
        error_indent = 9
        error_first_prefix = " " * error_indent + "  Error: "
        error_sec_prefix = " " * error_indent + "         "
        wrapper_first_error = textwrap.TextWrapper(initial_indent=error_first_prefix, width=preferred_width,
                                                   subsequent_indent=' ' * len(error_first_prefix))
        wrapper_sec_error = textwrap.TextWrapper(initial_indent=error_sec_prefix, width=preferred_width,
                                                 subsequent_indent=' ' * len(error_sec_prefix))

        # Log passed unit-tests
        headline_printed = False
        passed_printed = False
        for pkg, status in pkgs_status.items():
            if status.get("images"):
                if status.get("images")[0].get("pytest_json", {}).get("report", {}).get("tests"):
                    if (not headline_printed and self._verbose) and (EXIT_CODES["pytest"] & return_exit_code):
                        # Log unit-tests
                        sentence = " Unit Tests "
                        print(f"\n{Colors.Fg.cyan}{'#' * len(sentence)}")
                        print(f"{sentence}")
                        print(f"{'#' * len(sentence)}{Colors.reset}")
                        headline_printed = True
                    if not passed_printed:
                        print_v(f"\n{Colors.Fg.green}Passed Unit-tests:{Colors.reset}", log_verbose=self._verbose)
                        passed_printed = True
                    print_v(wrapper_pack.fill(f"{Colors.Fg.green}{pkg}{Colors.reset}"), log_verbose=self._verbose)
                    for image in status["images"]:
                        if not image.get("image_errors"):
                            tests = image.get("pytest_json", {}).get("report", {}).get("tests")
                            if tests:
                                print_v(wrapper_docker_image.fill(image['image']), log_verbose=self._verbose)
                                for test_case in tests:
                                    outcome = test_case.get("call", {}).get("outcome")
                                    if outcome != "failed":
                                        name = re.sub(pattern=r"\[.*\]",
                                                      repl="",
                                                      string=test_case.get("name"))
                                        if outcome and outcome != "passed":
                                            name = f'{name} ({outcome.upper()})'
                                        print_v(wrapper_test.fill(name), log_verbose=self._verbose)

        # Log failed unit-tests
        if EXIT_CODES["pytest"] & return_exit_code:
            if not headline_printed:
                # Log unit-tests
                sentence = " Unit Tests "
                print(f"\n{Colors.Fg.cyan}{'#' * len(sentence)}")
                print(f"{sentence}")
                print(f"{'#' * len(sentence)}{Colors.reset}")
            print(f"\n{Colors.Fg.red}Failed Unit-tests:{Colors.reset}")
            for fail_pack in lint_status["fail_packs_pytest"]:
                print(wrapper_pack.fill(f"{Colors.Fg.red}{fail_pack}{Colors.reset}"))
                for image in pkgs_status[fail_pack]["images"]:
                    tests = image.get("pytest_json", {}).get("report", {}).get("tests")
                    if tests:
                        for test_case in tests:
                            if test_case.get("call", {}).get("outcome") == "failed":
                                name = re.sub(pattern=r"\[.*\]",
                                              repl="",
                                              string=test_case.get("name"))
                                print(wrapper_test.fill(name))
                                if test_case.get("call", {}).get("longrepr"):
                                    print(wrapper_docker_image.fill(image['image']))
                                    for i in range(len(test_case.get("call", {}).get("longrepr"))):
                                        if i == 0:
                                            print(wrapper_first_error.fill(
                                                test_case.get("call", {}).get("longrepr")[i]))
                                        else:
                                            print(wrapper_sec_error.fill(test_case.get("call", {}).get("longrepr")[i]))
                                    print('\n')
                    else:
                        print(wrapper_docker_image.fill(image['image']))
                        errors = image.get("pytest_errors", {})
                        if errors:
                            print(wrapper_sec_error.fill(errors))

    @staticmethod
    def report_failed_image_creation(lint_status: dict, pkgs_status: dict, return_exit_code: int):
        """ Log failed image creation if occured

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
     """
        # Indentation config
        preferred_width = 100
        indent = 2
        pack_prefix = " " * indent + "- Package: "
        wrapper_pack = textwrap.TextWrapper(initial_indent=pack_prefix,
                                            width=preferred_width,
                                            subsequent_indent=' ' * len(pack_prefix))
        image_prefix = " " * indent + "  Image: "
        wrapper_image = textwrap.TextWrapper(initial_indent=image_prefix, width=preferred_width,
                                             subsequent_indent=' ' * len(image_prefix))
        indent_error = 4
        error_prefix = " " * indent_error + "  Error: "
        wrapper_error = textwrap.TextWrapper(initial_indent=error_prefix, width=preferred_width,
                                             subsequent_indent=' ' * len(error_prefix))
        # Log failed images creation
        if EXIT_CODES["image"] & return_exit_code:
            sentence = " Image creation errors "
            print(f"\n{Colors.Fg.red}{'#' * len(sentence)}{Colors.reset}")
            print(f"{Colors.Fg.red}{sentence}{Colors.reset}")
            print(f"{Colors.Fg.red}{'#' * len(sentence)}{Colors.reset}")
            for fail_pack in lint_status["fail_packs_image"]:
                print(wrapper_pack.fill(f"{Colors.Fg.cyan}{fail_pack}{Colors.reset}"))
                for image in pkgs_status[fail_pack]["images"]:
                    print(wrapper_image.fill(image["image"]))
                    print(wrapper_error.fill(image["image_errors"]))

    @staticmethod
    def report_summary(pkg, lint_status: dict, all_packs: bool = False):
        """ Log failed image creation if occured

        Args:
            lint_status(dict): Overall lint status
            all_packs(bool): True when running lint command with -a flag.
     """
        preferred_width = 100
        fail_pack_indent = 3
        fail_pack_prefix = " " * fail_pack_indent + "- "
        wrapper_fail_pack = textwrap.TextWrapper(initial_indent=fail_pack_prefix, width=preferred_width,
                                                 subsequent_indent=' ' * len(fail_pack_prefix))
        # intersection of all failed packages
        failed: Set[str] = set()

        # intersection of all warnings packages
        warnings: Set[str] = set()

        # each pack is checked for warnings and failures . A certain pack can appear in both failed packages and
        # warnings packages.
        for key in lint_status:
            if key.startswith('fail'):
                failed = failed.union(lint_status[key])
            if key.startswith('warning'):
                warnings = warnings.union(lint_status[key])
        # Log unit-tests summary
        sentence = " Summary "
        print(f"\n{Colors.Fg.cyan}{'#' * len(sentence)}")
        print(f"{sentence}")
        print(f"{'#' * len(sentence)}{Colors.reset}")
        print(f"Packages: {len(pkg)}")
        print(f"Packages PASS: {Colors.Fg.green}{len(pkg) - len(failed)}{Colors.reset}")
        print(f"Packages FAIL: {Colors.Fg.red}{len(failed)}{Colors.reset}")
        print(f"Packages WARNING (can either PASS or FAIL): {Colors.Fg.orange}{len(warnings)}{Colors.reset}\n")

        if not all_packs:
            if warnings:
                print("Warning packages:")
            for warning in warnings:
                print(f"{Colors.Fg.orange}{wrapper_fail_pack.fill(warning)}{Colors.reset}")

        if failed:
            print("Failed packages:")
        for fail_pack in failed:
            print(f"{Colors.Fg.red}{wrapper_fail_pack.fill(fail_pack)}{Colors.reset}")

    @staticmethod
    def _create_failed_packs_report(lint_status: dict, path: str):
        """
        Creates and saves a file containing all lint failed packs
        :param lint_status: dict
            Dictionary containing type of failures and corresponding failing tests. Looks like this:
             lint_status = {
            "fail_packs_flake8": [],
            "fail_packs_bandit": [],
            "fail_packs_mypy": [],
            "fail_packs_vulture": [],
            "fail_packs_pylint": [],
            "fail_packs_pytest": [],
            "fail_packs_pwsh_analyze": [],
            "fail_packs_pwsh_test": [],
            "fail_packs_image": []
        }
        :param path: str
            The path to save the report.
        """
        failed_ut: set = set()
        for key in lint_status:
            if key.startswith('fail'):
                failed_ut = failed_ut.union(lint_status[key])
        if path and failed_ut:
            file_path = Path(path) / "failed_lint_report.txt"
            file_path.write_text('\n'.join(failed_ut))

    def create_json_output(self):
        """Creates a JSON file output for lints"""
        if not self.json_file_path:
            return

        if os.path.exists(self.json_file_path):
            json_contents = get_json(self.json_file_path)
            if not (isinstance(json_contents, list)):
                json_contents = []
        else:
            json_contents = []
        logger.info('Collecting results to write to file')
        # format all linters to JSON format -
        # if any additional linters are added, please add a formatting function here
        for check in self.linters_error_list:
            if check.get('linter') == 'flake8':
                self.flake8_error_formatter(check, json_contents)
            elif check.get('linter') == 'mypy':
                self.mypy_error_formatter(check, json_contents)
            elif check.get('linter') == 'bandit':
                self.bandit_error_formatter(check, json_contents)
            elif check.get('linter') == 'vulture':
                self.vulture_error_formatter(check, json_contents)
            elif check.get('linter') == 'XSOAR_linter':
                self.xsoar_linter_error_formatter(check, json_contents)
        with open(self.json_file_path, 'w+') as f:
            json.dump(json_contents, f, indent=4)

        logger.info(f'Logs saved to {self.json_file_path}')

    def flake8_error_formatter(self, errors: Dict, json_contents: List) -> None:
        """Format flake8 error strings to JSON format and add them the json_contents

        Args:
            errors (Dict): A dictionary containing flake8 error strings
            json_contents (List): The JSON file outputs
        """
        error_messages = errors.get('messages', '')
        error_messages = error_messages.split('\n') if error_messages else []
        for message in error_messages:
            if message:
                file_path, line_number, column_number, _ = message.split(':', 3)
                code = message.split()[1]
                output = {
                    'linter': 'flake8',
                    'severity': errors.get('type'),
                    'errorCode': code,
                    'message': message.split(code)[1].lstrip(),
                    'row': line_number,
                    'col': column_number
                }
                self.add_to_json_outputs(output, file_path, json_contents)

    @staticmethod
    def gather_mypy_errors(error_messages: List) -> List:
        """Gather multi-line mypy errors to a single line

        Args:
            error_messages (List): A list of mypy error outputs

        Returns:
            List. A list of strings, each element is a full mypy error message
        """
        mypy_errors: list = []
        gather_error: list = []
        for line in error_messages:
            if os.path.isfile(line.split(':')[0]):
                if gather_error:
                    mypy_errors.append('\n'.join(gather_error))
                    gather_error = []
            gather_error.append(line)

        # handle final error
        # last line is irrelevant
        if gather_error:
            mypy_errors.append('\n'.join(gather_error[:-1]))

        return mypy_errors

    def mypy_error_formatter(self, errors: Dict, json_contents: List) -> None:
        """Format mypy error strings to JSON format and add them the json_contents

        Args:
            errors (Dict): A dictionary containing mypy error strings
            json_contents (List): The JSON file outputs
        """
        error_messages = errors.get('messages', '')
        error_messages = error_messages.split('\n') if error_messages else []
        mypy_errors = self.gather_mypy_errors(error_messages)

        for message in mypy_errors:
            if message:
                file_path, line_number, column_number, _ = message.split(':', 3)
                output_message = message.split('error:')[1].lstrip() if 'error' in message \
                    else message.split('note:')[1].lstrip()
                output = {
                    'linter': 'mypy',
                    'severity': errors.get('type'),
                    'message': output_message,
                    'row': line_number,
                    'col': column_number
                }
                self.add_to_json_outputs(output, file_path, json_contents)

    def bandit_error_formatter(self, errors: Dict, json_contents: List) -> None:
        """Format bandit error strings to JSON format and add them the json_contents

        Args:
            errors (Dict): A dictionary containing bandit error strings
            json_contents (List): The JSON file outputs
        """
        error_messages = errors.get('messages', '')
        error_messages = error_messages.split('\n') if error_messages else []
        for message in error_messages:
            if message:
                file_path, line_number, _ = message.split(':', 2)
                output = {
                    'linter': 'bandit',
                    'severity': errors.get('type'),
                    'errorCode': message.split(' ')[1],
                    'message': message.split('[')[1].replace(']', ' -'),
                    'row': line_number,
                }
                self.add_to_json_outputs(output, file_path, json_contents)

    @staticmethod
    def get_full_file_path_for_vulture(file_name: str, content_path: str) -> str:
        """Get the full file path to a file with a given name name from the content path

        Args:
            file_name (str): The file name of the file to find
            content_path (str): The content file path

        Returns:
            str. The path to the file
        """
        file_ending = retrieve_file_ending(file_name)
        if not file_ending:
            file_name = f'{file_name}.py'
        elif file_ending != 'py':
            file_name = file_name.replace(file_ending, 'py')
        return find_file(content_path, file_name)

    def vulture_error_formatter(self, errors: Dict, json_contents: List) -> None:
        """Format vulture error strings to JSON format and add them the json_contents

        Args:
            errors (Dict): A dictionary containing vulture error strings
            json_contents (List): The JSON file outputs
        """
        error_messages = errors.get('messages', '')
        error_messages = error_messages.split('\n') if error_messages else []
        content_path = get_content_path()
        for message in error_messages:
            if message:
                file_name, line_number, error_contents = message.split(':', 2)
                file_path = self.get_full_file_path_for_vulture(file_name, content_path)
                output = {
                    'linter': 'vulture',
                    'severity': errors.get('type'),
                    'message': error_contents.lstrip(),
                    'row': line_number,
                }
                self.add_to_json_outputs(output, file_path, json_contents)

    def xsoar_linter_error_formatter(self, errors: Dict, json_contents: List) -> None:
        """Format XSOAR linter error strings to JSON format and add them the json_contents

        Args:
            errors (Dict): A dictionary containing XSOAR linter error strings
            json_contents (List): The JSON file outputs
        """
        error_messages = errors.get('messages', '')
        error_messages = error_messages.split('\n') if error_messages else []
        for message in error_messages:
            if message:
                split_message = message.split(':')
                file_path = split_message[0] if len(split_message) >= 1 else ''
                code = message.split(' ')[1] if len(message.split(' ')) >= 2 else ''
                output = {
                    'linter': 'xsoar_linter',
                    'severity': errors.get('type'),
                    'errorCode': code,
                    'message': message.split(code)[-1].lstrip() if len(message.split(code)) >= 1 else '',
                    'row': split_message[1] if len(split_message) >= 2 else '',
                    'col': split_message[2] if len(split_message) >= 3 else ''
                }
                self.add_to_json_outputs(output, file_path, json_contents)

    @staticmethod
    def add_to_json_outputs(output: Dict, file_path: str, json_contents: List):
        """Adds an error entry to the JSON file contents

        Args:
            output (Dict): The information about an error entry
            file_path (str): The file path where the error occurred
            json_contents (List): The JSON file outputs
        """
        yml_file_path = file_path.replace('.py', '.yml').replace('.ps1', '.yml')
        file_type = find_type(yml_file_path)
        full_error_output = {
            'filePath': file_path,
            'fileType': os.path.splitext(file_path)[1].replace('.', ''),
            'entityType': file_type.value if file_type else '',
            'errorType': 'Code',
            'name': get_file_displayed_name(yml_file_path),  # type: ignore[arg-type]
            **output
        }
        json_contents.append(full_error_output)
