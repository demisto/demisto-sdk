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
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (PACKS_PACK_META_FILE_NAME,
                                                   TYPE_PWSH, TYPE_PYTHON)
# Local packages
from demisto_sdk.commands.common.logger import Colors, logging_setup
from demisto_sdk.commands.common.tools import (print_error, print_v,
                                               print_warning)
from demisto_sdk.commands.lint.helpers import (EXIT_CODES, PWSH_CHECKS,
                                               PY_CHCEKS,
                                               build_skipped_exit_code,
                                               get_test_modules, validate_env)
from demisto_sdk.commands.lint.linter import Linter
from wcmatch.pathlib import Path

logger: logging.Logger


class LintManager:
    """ LintManager used to activate lint command using Linters in a single or multi thread.

    Attributes:
        input(str): Directories to run lint on.
        git(bool): Perform lint and test only on chaged packs.
        all_packs(bool): Whether to run on all packages.
        verbose(int): Whether to output a detailed response.
        quiet(bool): Whether to output a quiet response.
        log_path(str): Path to all levels of logs.
    """

    def __init__(self, input: str, git: bool, all_packs: bool, quiet: bool, verbose: int, log_path: str):
        # Set logging level and file handler if required
        global logger
        logger = logging_setup(verbose=verbose,
                               quiet=quiet,
                               log_path=log_path)
        # Verbosity level
        self._verbose = not quiet if quiet else verbose
        # Gather facts for manager
        self._facts: dict = self._gather_facts()
        # Filter packages to lint and test check
        self._pkgs: List[Path] = self._get_packages(content_repo=self._facts["content_repo"],
                                                    input=input,
                                                    git=git,
                                                    all_packs=all_packs)

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
            is_external_repo = tools.is_external_repository()

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
        except git.GitCommandError as e:
            print_error(
                "Unable to get test-modules demisto-mock.py etc - Aborting! corrupt repository of pull from master")
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
        except (requests.exceptions.ConnectionError, urllib3.exceptions.ProtocolError, docker.errors.APIError):
            facts["docker_engine"] = False
            print_warning("Can't communicate with Docker daemon - check your docker Engine is ON - Skipping lint, "
                          "test which require docker!")
            logger.info("demisto-sdk-Can't communicate with Docker daemon")
        logger.debug("Docker daemon test passed")

        return facts

    def _get_packages(self, content_repo: git.Repo, input: str, git: bool, all_packs: bool) -> List[Path]:
        """ Get packages paths to run lint command.

        Args:
            content_repo(git.Repo): Content repository object.
            input(str): dir pack specified as argument.
            git(bool): Perform lint and test only on changed packs.
            all_packs(bool): Whether to run on all packages.

        Returns:
            List[Path]: Pkgs to run lint
        """
        pkgs: list
        if all_packs or git:
            pkgs = LintManager._get_all_packages(content_dir=content_repo.working_dir)
        elif not all_packs and not git and not input:
            pkgs = [Path().cwd()]
        else:
            pkgs = []
            for item in input.split(','):
                is_pack = os.path.isdir(item) and os.path.exists(os.path.join(item, PACKS_PACK_META_FILE_NAME))
                if is_pack:
                    pkgs.extend(LintManager._get_all_packages(content_dir=item))
                else:
                    pkgs.append(Path(item))

        total_found = len(pkgs)
        if git:
            pkgs = LintManager._filter_changed_packages(content_repo=content_repo,
                                                        pkgs=pkgs)
            for pkg in pkgs:
                print_v(f"Found changed package {Colors.Fg.cyan}{pkg}{Colors.reset}",
                        log_verbose=self._verbose)
        print(f"Execute lint and test on {Colors.Fg.cyan}{len(pkgs)}/{total_found}{Colors.reset} packages")

        return pkgs

    @staticmethod
    def _get_all_packages(content_dir: str) -> List[str]:
        """Gets all integration, script in packages and packs in content repo.

        Returns:
            list: A list of integration, script and beta_integration names.
        """
        # ￿Get packages from main content path
        content_main_pkgs: set = set(Path(content_dir).glob(['Integrations/*/',
                                                             'Scripts/*/', ]))
        # Get packages from packs path
        packs_dir: Path = Path(content_dir) / 'Packs'
        content_packs_pkgs: set = set(packs_dir.glob(['*/Integrations/*/',
                                                      '*/Scripts/*/']))
        all_pkgs = content_packs_pkgs.union(content_main_pkgs)

        return list(all_pkgs)

    @staticmethod
    def _filter_changed_packages(content_repo: git.Repo, pkgs: List[Path]) -> List[Path]:
        """ Checks which packages had changes using git (working tree, index, diff between HEAD and master in them and should
        run on Lint.

        Args:
            pkgs(List[Path]): pkgs to check

        Returns:
            List[Path]: A list of names of packages that should run.
        """
        print(f"Comparing to {Colors.Fg.cyan}{content_repo.remote()}/master{Colors.reset} using branch {Colors.Fg.cyan}"
              f"{content_repo.active_branch}{Colors.reset}")
        staged_files = {content_repo.working_dir / Path(item.b_path).parent for item in
                        content_repo.active_branch.commit.tree.diff(None, paths=pkgs)}
        if content_repo.active_branch != content_repo.heads.master:
            last_common_commit = content_repo.merge_base(content_repo.active_branch.commit,
                                                         content_repo.remote().refs.master)
        else:
            last_common_commit = content_repo.remote().refs.master.commit.parents[0]
        changed_from_master = {content_repo.working_dir / Path(item.b_path).parent for item in
                               content_repo.active_branch.commit.tree.diff(last_common_commit, paths=pkgs)}
        all_changed = staged_files.union(changed_from_master)
        pkgs_to_check = all_changed.intersection(pkgs)

        return list(pkgs_to_check)

    def run_dev_packages(self, parallel: int, no_flake8: bool, no_bandit: bool, no_mypy: bool, no_pylint: bool,
                         no_vulture: bool, no_test: bool, no_pwsh_analyze: bool, no_pwsh_test: bool,
                         keep_container: bool,
                         test_xml: str, failure_report: str) -> int:
        """ Runs the Lint command on all given packages.

        Args:
            parallel(int): Whether to run command on multiple threads
            no_flake8(bool): Whether to skip flake8
            no_bandit(bool): Whether to skip bandit
            no_mypy(bool): Whether to skip mypy
            no_vulture(bool): Whether to skip vulture
            no_pylint(bool): Whether to skip pylint
            no_test(bool): Whether to skip pytest
            no_pwsh_analyze(bool): Whether to skip powershell code analyzing
            no_pwsh_test(bool): whether to skip powershell tests
            keep_container(bool): Whether to keep the test container
            test_xml(str): Path for saving pytest xml results
            failure_report(str): Path for store failed packs report

        Returns:
            int: exit code by fail exit codes by var EXIT_CODES
        """
        lint_status: Dict = {
            "fail_packs_flake8": [],
            "fail_packs_bandit": [],
            "fail_packs_mypy": [],
            "fail_packs_vulture": [],
            "fail_packs_pylint": [],
            "fail_packs_pytest": [],
            "fail_packs_pwsh_analyze": [],
            "fail_packs_pwsh_test": [],
            "fail_packs_image": [],
        }

        # Python or powershell or both
        pkgs_type = []

        # Detailed packages status
        pkgs_status = {}

        # Skiped lint and test codes
        skipped_code = build_skipped_exit_code(no_flake8=no_flake8, no_bandit=no_bandit, no_mypy=no_mypy,
                                               no_vulture=no_vulture,
                                               no_pylint=no_pylint, no_test=no_test, no_pwsh_analyze=no_pwsh_analyze,
                                               no_pwsh_test=no_pwsh_test, docker_engine=self._facts["docker_engine"])

        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
            return_exit_code: int = 0
            results = []
            # Executing lint checks in different threads
            for pack in self._pkgs:
                linter: Linter = Linter(pack_dir=pack,
                                        content_repo="" if not self._facts["content_repo"] else
                                        Path(self._facts["content_repo"].working_dir),
                                        req_2=self._facts["requirements_2"],
                                        req_3=self._facts["requirements_3"],
                                        docker_engine=self._facts["docker_engine"])
                results.append(executor.submit(fn=linter.run_dev_packages,
                                               no_flake8=no_flake8,
                                               no_bandit=no_bandit,
                                               no_mypy=no_mypy,
                                               no_vulture=no_vulture,
                                               no_pylint=no_pylint,
                                               no_test=no_test,
                                               no_pwsh_analyze=no_pwsh_analyze,
                                               no_pwsh_test=no_pwsh_test,
                                               modules=self._facts["test_modules"],
                                               keep_container=keep_container,
                                               test_xml=test_xml))
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
                             skipped_code=int(skipped_code),
                             pkgs_type=pkgs_type)
        self._create_failed_packs_report(lint_status=lint_status, path=failure_report)

        return return_exit_code

    def _report_results(self, lint_status: dict, pkgs_status: dict, return_exit_code: int, skipped_code: int,
                        pkgs_type: list):
        """ Log report to console

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
            skipped_code(int): skipped test code
            pkgs_type(list): list determine which pack type exits.

     """
        self.report_pass_lint_checks(return_exit_code=return_exit_code,
                                     skipped_code=skipped_code,
                                     pkgs_type=pkgs_type)
        self.report_failed_lint_checks(return_exit_code=return_exit_code,
                                       pkgs_status=pkgs_status,
                                       lint_status=lint_status)
        self.report_unit_tests(return_exit_code=return_exit_code,
                               pkgs_status=pkgs_status,
                               lint_status=lint_status)
        self.report_failed_image_creation(return_exit_code=return_exit_code,
                                          pkgs_status=pkgs_status,
                                          lint_status=lint_status)
        self.report_summary(lint_status=lint_status)

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

    @staticmethod
    def report_failed_lint_checks(lint_status: dict, pkgs_status: dict, return_exit_code: int):
        """ Log failed lint log if exsits

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
        """
        for check in ["flake8", "bandit", "mypy", "vulture"]:
            if EXIT_CODES[check] & return_exit_code:
                sentence = f" {check.capitalize()} errors "
                print(f"\n{Colors.Fg.red}{'#' * len(sentence)}{Colors.reset}")
                print(f"{Colors.Fg.red}{sentence}{Colors.reset}")
                print(f"{Colors.Fg.red}{'#' * len(sentence)}{Colors.reset}\n")
                for fail_pack in lint_status[f"fail_packs_{check}"]:
                    print(f"{Colors.Fg.red}{pkgs_status[fail_pack]['pkg']}{Colors.reset}")
                    print(pkgs_status[fail_pack][f"{check}_errors"])

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
                                    if test_case.get("call", {}).get("outcome") != "failed":
                                        name = re.sub(pattern=r"\[.*\]",
                                                      repl="",
                                                      string=test_case.get("name"))
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

    def report_summary(self, lint_status: dict):
        """ Log failed image creation if occured

        Args:
            lint_status(dict): Overall lint status
     """
        preferred_width = 100
        fail_pack_indent = 3
        fail_pack_prefix = " " * fail_pack_indent + "- "
        wrapper_fail_pack = textwrap.TextWrapper(initial_indent=fail_pack_prefix, width=preferred_width,
                                                 subsequent_indent=' ' * len(fail_pack_prefix))
        # intersection of all failed packages
        failed: Set[str] = set()
        for packs in lint_status.values():
            failed = failed.union(packs)
        # Log unit-tests summary
        sentence = " Summary "
        print(f"\n{Colors.Fg.cyan}{'#' * len(sentence)}")
        print(f"{sentence}")
        print(f"{'#' * len(sentence)}{Colors.reset}")
        print(f"Packages: {len(self._pkgs)}")
        print(f"Packages PASS: {Colors.Fg.green}{len(self._pkgs) - len(failed)}{Colors.reset}")
        print(f"Packages FAIL: {Colors.Fg.red}{len(failed)}{Colors.reset}")
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
        failed_ut: Set[Any] = set().union([second_val for val in lint_status.values() for second_val in val])
        if path and failed_ut:
            file_path = Path(path) / "failed_lint_report.txt"
            file_path.write_text('\n'.join(failed_ut))
