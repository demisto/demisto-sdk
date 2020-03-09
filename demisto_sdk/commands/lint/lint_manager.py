# STD packages
import concurrent.futures
import json
import logging
import os
import sys
import textwrap
from typing import List
import git
import re
# Third party packages
import docker
from wcmatch.pathlib import Path
# Local packages
from demisto_sdk.commands.common.logger import Colors, logging_setup
from demisto_sdk.commands.common.tools import print_v, print_error
from demisto_sdk.commands.lint.helpers import get_test_modules, FAIL_EXIT_CODES
from demisto_sdk.commands.lint.linter import Linter

logger: logging.Logger


class LintManager:
    """ LintManager used to activate lint command using Linters in a single or multi thread.

    Attributes:
        dir_packs(str): Directories to run lint on.
        git(bool): Perform lint and test only on chaged packs.
        all_packs(bool): Whether to run on all packages.
        verbose(int): Whether to output a detailed response.
        log_path(str): Path to all levels of logs.
    """

    def __init__(self, dir_packs: str, git: bool, all_packs: bool, verbose: bool, log_path: str):
        self._verbose = verbose
        # Set logging level and file handler if required
        global logger
        logger = logging_setup(verbose=verbose,
                               log_path=log_path)
        # Gather facts for manager
        self._facts: dict = self._gather_facts()
        # Filter packages to lint and test check
        self._pkgs: List[Path] = self._get_packages(content_repo=self._facts["content_repo"],
                                                    dir_packs=dir_packs,
                                                    git=git,
                                                    all_packs=all_packs)

    @staticmethod
    def _gather_facts():
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
            "test_modules": None
        }
        # Get content repo object
        try:
            git_repo = git.Repo(os.getcwd(),
                                search_parent_directories=True)
            if 'content' not in git_repo.remote().urls.__next__():
                raise git.InvalidGitRepositoryError
            facts["content_repo"] = git_repo
            logger.info(f"lint - Content path {git_repo.working_dir}")
        except (git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
            print_error("Please run demisto-sdk lint in content repository - Aborting!")
            logger.critical(f"demisto-sdk-lint - can't locate content repo {e}")
            sys.exit(1)
        # Get global requirements file
        pipfile_dir = Path(__file__).parent / 'dev_envs'
        try:
            for py_num in ['2', '3']:
                pipfile_lock_path = pipfile_dir / f'default_python{py_num}/Pipfile.lock'
                with open(file=pipfile_lock_path) as f:
                    lock_file: dict = json.load(fp=f)["develop"]
                    facts[f"requirements_{py_num}"] = [key + value["version"] for key, value in lock_file.items()]
                    logger.info(f"lint - Test requirement successfully collected for python {py_num}")
                    logger.debug(f"lint - Test requirement are {facts[f'requirements_{py_num}']}")
        except (json.JSONDecodeError, IOError, FileNotFoundError, KeyError) as e:
            print_error("Can't parse pipfile.lock - Aborting!")
            logger.critical(f"demisto-sdk-lint - can't parse pipfile.lock {e}")
            sys.exit(1)
        # ￿Get mandatory modulestest modules and Internet connection for docker usage
        try:
            facts["test_modules"] = get_test_modules(content_repo=facts["content_repo"])
            logger.info(f"lint - Test mandatory modules successfully collected")
        except git.GitCommandError as e:
            print_error("Unable to get mandatory test-modules demisto-mock.py etc - Aborting! (Check your internet "
                        "connection)")
            logger.critical(f"demisto-sdk-lint - unable to get mandatory test-modules demisto-mock.py etc {e}",
                            exc_info=False)
            sys.exit(1)
        # Validating docker engine connection
        docker_client: docker.DockerClient = docker.from_env()
        daemon_connection = docker_client.ping()
        if not daemon_connection:
            print_error("Can't communicate with Docker daemon - check your docker Engine is ON - Aborting!")
            logger.critical(f"demisto-sdk-lint - Can't communicate with Docker daemon")
            sys.exit(1)
        logger.info(f"lint - Docker daemon test passed")

        return facts

    def _get_packages(self, content_repo: git.Repo, dir_packs: str, git: bool, all_packs: bool) -> List[Path]:
        """ Get packages paths to run lint command.

        Args:
            content_repo(git.Repo): Content repository object.
            dir_packs(str): dir packs list specified as argument.
            git(bool): Perform lint and test only on chaged packs.
            all_packs(bool): Whether to run on all packages.

        Returns:
            List[Path]: Pkgs to run lint
        """
        pkgs: list
        if (all_packs or git) and not dir_packs:
            pkgs = LintManager._get_all_packages(content_dir=content_repo.working_dir)
        else:
            pkgs = [Path(item) for item in dir_packs.split(',')]
        total_found = len(pkgs)
        print(f"Total content packages found {Colors.Fg.cyan}{total_found}{Colors.reset}")
        if git:
            pkgs = LintManager._filter_changed_packages(content_repo=content_repo,
                                                        pkgs=pkgs)
            for pkg in pkgs:
                print_v(f"Package added after comparing to git {Colors.Fg.cyan}{pkg}{Colors.reset}",
                        log_verbose=self._verbose)
        print(f"Execute lint and test on {Colors.Fg.cyan}{len(pkgs)}/{total_found}{Colors.reset} "
              f"packages")

        return pkgs

    @staticmethod
    def _get_all_packages(content_dir: str) -> List[str]:
        """Gets all integration, script and beta_integrations in packages and packs in content repo.

        Returns:
            list: A list of integration, script and beta_integration names.
        """
        # ￿Get packages from main content path
        content_main_pkgs: set = set(Path(content_dir).glob(['Integrations/*/',
                                                             'Scripts/*/',
                                                             'Beta_Integrations/*/']))
        # Get packages from packs path
        packs_dir: Path = Path(content_dir) / 'Packs'
        content_packs_pkgs: set = set(packs_dir.rglob(['Integrations/*/',
                                                       'Scripts/*/',
                                                       'Beta_Integrations/*/']))
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
        print(f"Comparing to git using branch {Colors.Fg.cyan}{content_repo.active_branch}{Colors.reset}")
        untracked_files = [Path(item) for item in content_repo.untracked_files]
        staged_files = {Path(item.b_path).parent for item in content_repo.index.diff(None, paths=pkgs)}
        changed_from_master = {Path(item.b_path).parent for item in content_repo.head.commit.diff('origin/master',
                                                                                                  paths=pkgs)}
        all_changed = set(untracked_files).union(staged_files).union(changed_from_master)
        pkgs_to_check = all_changed.intersection(pkgs)

        return list(pkgs_to_check)

    def run_dev_packages(self, parallel: int, no_flake8: bool, no_bandit: bool, no_mypy: bool, no_pylint: bool,
                         no_vulture: bool, no_test: bool, keep_container: bool, test_xml: str, json_report: str) -> int:
        """ Runs the Lint command on all given packages.

        Args:
            parallel(int): Whether to run command on multiple threads.
            no_flake8(bool): Whether to skip flake8.
            no_bandit(bool): Whether to skip bandit.
            no_mypy(bool): Whether to skip mypy.
            no_vulture(bool): Whether to skip vulture
            no_pylint(bool): Whether to skip pylint.
            no_test(bool): Whether to skip pytest.
            keep_container(bool): Whether to keep the test container.
            test_xml(str): Path for saving pytest xml results.
            json_report(str): Path for store json report.

        Returns:
            int: exit code by falil exit codes by var FAIL_EXIT_CODES
        """
        lint_status = {
            "fail_packs_flake8": [],
            "fail_packs_bandit": [],
            "fail_packs_mypy": [],
            "fail_packs_pylint": [],
            "fail_packs_pytest": [],
            "fail_packs_image": [],
        }
        # Detailed packages status
        pkgs_status = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
            return_exit_code: int = 0
            results = []
            for pack in self._pkgs:
                print_v(f"Permform lint on {Colors.Fg.cyan}{pack}{Colors.reset}", log_verbose=self._verbose)
                linter: Linter = Linter(pack_dir=pack,
                                        content_path=Path(self._facts["content_repo"].working_dir),
                                        req_2=self._facts["requirements_2"],
                                        req_3=self._facts["requirements_3"])
                results.append(executor.submit(fn=linter.run_dev_packages,
                                               no_flake8=no_flake8,
                                               no_bandit=no_bandit,
                                               no_mypy=no_mypy,
                                               no_vulture=no_vulture,
                                               no_pylint=no_pylint,
                                               no_test=no_test,
                                               modules=self._facts["test_modules"],
                                               keep_container=keep_container,
                                               test_xml=test_xml))
            counter = 0
            for future in concurrent.futures.as_completed(results):
                exit_code, pkg_status = future.result()
                pkgs_status[pkg_status["pkg"]] = pkg_status
                if exit_code:
                    if exit_code & FAIL_EXIT_CODES["flake8"]:
                        lint_status["fail_packs_flake8"].append(pkg_status["pkg"])
                    if exit_code & FAIL_EXIT_CODES["bandit"]:
                        lint_status["fail_packs_bandit"].append(pkg_status["pkg"])
                    if exit_code & FAIL_EXIT_CODES["mypy"]:
                        lint_status["fail_packs_mypy"].append(pkg_status["pkg"])
                    if exit_code & FAIL_EXIT_CODES["mypy"]:
                        lint_status["fail_packs_vulture"].append(pkg_status["pkg"])
                    if exit_code & FAIL_EXIT_CODES["pylint"]:
                        lint_status["fail_packs_pylint"].append(pkg_status["pkg"])
                    if exit_code & FAIL_EXIT_CODES["pytest"]:
                        lint_status["fail_packs_pytest"].append(pkg_status["pkg"])
                    if exit_code & FAIL_EXIT_CODES["image"]:
                        lint_status["fail_packs_image"].append(pkg_status["pkg"])
                    if not return_exit_code & exit_code:
                        return_exit_code += exit_code
                counter += 1

        self._report_results(lint_status=lint_status,
                             pkgs_status=pkgs_status,
                             return_exit_code=return_exit_code)
        LintManager._create_report(pkgs_status=pkgs_status,
                                   path=json_report)

        return return_exit_code

    def _report_results(self, lint_status: dict, pkgs_status: dict, return_exit_code: int):
        """ Log report to console

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
     """
        self.report_pass_lint_checks(return_exit_code=return_exit_code)
        self.report_failed_lint_checks(return_exit_code=return_exit_code,
                                       pkgs_status=pkgs_status,
                                       lint_status=lint_status)
        self.report_unit_tests(return_exit_code=return_exit_code,
                               pkgs_status=pkgs_status,
                               lint_status=lint_status)
        self.report_failed_image_creation(return_exit_code=return_exit_code,
                                          pkgs_status=pkgs_status,
                                          lint_status=lint_status)

    @staticmethod
    def report_pass_lint_checks(return_exit_code: int):
        """ Log PASS/FAIL on each lint/test

        Args:
            return_exit_code(int): exit code will indicate which lint or test failed
         """
        for lint in ["flake8", "bandit", "mypy", "vulture", "pylint", "pytest"]:
            spacing = 7 - len(lint)
            if not FAIL_EXIT_CODES[lint] & return_exit_code:
                print(f"{lint} {' ' * spacing}- {Colors.Bg.green}[PASS]{Colors.reset}")
            else:
                print(f"{lint} {' ' * spacing}- {Colors.Bg.red}[FAIL]{Colors.reset}")

    @staticmethod
    def report_failed_lint_checks(lint_status: dict, pkgs_status: dict, return_exit_code: int):
        """ Log failed lint log if exsits

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
        """
        for lint in ["flake8", "bandit", "mypy", "vulture"]:
            if FAIL_EXIT_CODES[lint] & return_exit_code:
                sentence = f" {lint.capitalize()} errors "
                print(f"\n{Colors.Fg.cyan}{'#' * len(sentence)}{Colors.reset}")
                print(f"{Colors.Fg.cyan}{sentence}{Colors.reset}")
                print(f"{Colors.Fg.cyan}{'#' * len(sentence)}{Colors.reset}")
                for fail_pack in lint_status[f"fail_packs_{lint}"]:
                    print(f"{Colors.Fg.cyan}{pkgs_status[fail_pack]['pkg']}{Colors.reset}")
                    print(pkgs_status[fail_pack][f"{lint}_errors"])

        if FAIL_EXIT_CODES["pylint"] & return_exit_code:
            sentence = f" Pylint errors "
            print(f"\n{Colors.Fg.cyan}{'#' * len(sentence)}{Colors.reset}")
            print(f"{Colors.Fg.cyan}{sentence}{Colors.reset}")
            print(f"{Colors.Fg.cyan}{'#' * len(sentence)}{Colors.reset}")
            for fail_pack in lint_status[f"fail_packs_pylint"]:
                print(f"{Colors.Fg.cyan}{fail_pack}{Colors.reset}")
                print(pkgs_status[fail_pack]["images"][0]["pylint_errors"])

    def report_unit_tests(self, lint_status: dict, pkgs_status: dict, return_exit_code: int):
        """ Log failed unit-tests , if verbosity specified will log also success unit-tests

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
        """
        # Indentation config
        packs_with_tests = 0
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
        # Log unit-tests
        sentence = " Unit Tests "
        print(f"\n{Colors.Fg.cyan}{'#' * len(sentence)}")
        print(f"{sentence}")
        print(f"{'#' * len(sentence)}{Colors.reset}")
        # Log passed unit-tests
        passed_printed = False
        for pkg, status in pkgs_status.items():
            if status.get("images")[0].get("pytest_json", {}).get("report", {}).get("tests"):
                if not passed_printed:
                    print_v(f"\n{Colors.Fg.blue}Passed Unit-tests:{Colors.reset}", log_verbose=self._verbose)
                    passed_printed = True
                print_v(wrapper_pack.fill(f"{Colors.Fg.cyan}{pkg}{Colors.reset}"), log_verbose=self._verbose)
                for image in status["images"]:
                    if not image.get("image_errors"):
                        tests = image.get("pytest_json", {}).get("report", {}).get("tests")
                        if tests:
                            print_v(wrapper_docker_image.fill(image['image']), log_verbose=self._verbose)
                            if not FAIL_EXIT_CODES["pytest"] & status["exit_code"]:
                                packs_with_tests += 1
                            for test_case in tests:
                                if test_case.get("call", {}).get("outcome") != "failed":
                                    name = re.sub(pattern=r"\[.*\]",
                                                  repl="",
                                                  string=test_case.get("name"))
                                    print_v(wrapper_test.fill(name), log_verbose=self._verbose)

        # Log failed unit-tests
        if FAIL_EXIT_CODES["pytest"] & return_exit_code:
            print(f"\n{Colors.Fg.blue}Failed Unit-tests:{Colors.reset}")
            for fail_pack in lint_status["fail_packs_pytest"]:
                packs_with_tests += 1
                print(wrapper_pack.fill(f"{Colors.Fg.cyan}{fail_pack}{Colors.reset}"))
                for image in pkgs_status[fail_pack]["images"]:
                    tests = image.get("pytest_json", {}).get("report", {}).get("tests")
                    for test_case in tests:
                        if test_case.get("call", {}).get("outcome") == "failed":
                            name = re.sub(pattern=r"\[.*\]",
                                          repl="",
                                          string=test_case.get("name"))
                            print(wrapper_test.fill(name))
                            if test_case.get("call", {}).get("longrepr"):
                                for i in range(len(test_case.get("call", {}).get("longrepr"))):
                                    if i == 0:
                                        print(wrapper_first_error.fill(
                                            test_case.get("call", {}).get("longrepr")[i]))
                                    else:
                                        print(wrapper_sec_error.fill(test_case.get("call", {}).get("longrepr")[i]))

        # Log unit-tests summary
        print(f"\n{Colors.Fg.blue}Summary:{Colors.reset}")
        print(f"Packages: {len(pkgs_status)}")
        print(f"Packages with unit-tests: {packs_with_tests}")
        print(f"   Pass: {Colors.Fg.green}{packs_with_tests - len(lint_status['fail_packs_pytest'])}"
              f"{Colors.reset}")
        print(f"   Failed: {Colors.Fg.red}{len(lint_status['fail_packs_pytest'])}{Colors.reset}")
        if lint_status['fail_packs_pytest']:
            print(f"Failed packages:")
            preferred_width = 100
            fail_pack_indent = 3
            fail_pack_prefix = " " * fail_pack_indent + "- "
            wrapper_fail_pack = textwrap.TextWrapper(initial_indent=fail_pack_prefix, width=preferred_width,
                                                     subsequent_indent=' ' * len(fail_pack_prefix))
            for fail_pack in lint_status["fail_packs_pytest"]:
                print(wrapper_fail_pack.fill(fail_pack))

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
        if FAIL_EXIT_CODES["image"] & return_exit_code:
            sentence = f" Image creation errors "
            print(f"\n{Colors.Fg.cyan}{'#' * len(sentence)}{Colors.reset}")
            print(f"{Colors.Fg.cyan}{sentence}{Colors.reset}")
            print(f"{Colors.Fg.cyan}{'#' * len(sentence)}{Colors.reset}")
            for fail_pack in lint_status["fail_packs_image"]:
                print(wrapper_pack.fill(f"{Colors.Fg.cyan}{fail_pack}{Colors.reset}"))
                for image in pkgs_status[fail_pack]["images"]:
                    print(wrapper_image.fill(image["image"]))
                    print(wrapper_error.fill(image["image_errors"]))

    @staticmethod
    def _create_report(pkgs_status: dict, path: str):
        if path:
            json_path = Path(path) / "lint_report.json"
            json.dump(fp=json_path.open(mode='w'),
                      obj=pkgs_status,
                      indent=4,
                      sort_keys=True)
