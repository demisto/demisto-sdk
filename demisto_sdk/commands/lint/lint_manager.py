# STD python packages
import concurrent
import os
import concurrent.futures.thread
from typing import List, Dict, Any, Optional
import logging
import time
# 3-rd party packages
import docker
from jinja2 import Environment, FileSystemLoader
from tqdm import tqdm
# Local packages
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import PACKS_DIR, INTEGRATIONS_DIR, SCRIPTS_DIR, BETA_INTEGRATIONS_DIR
from demisto_sdk.commands.common.logger import Colors, logging_setup
from demisto_sdk.commands.common.tools import get_dev_requirements, run_command
from demisto_sdk.commands.lint.linter import Linter

# Logger object init
logger: logging.Logger


class LintManager:
    """LintManager used to activate lint command using Linters in a single or multi thread.

    Attributes:
        dir_packs: A CSV of directories to run lint on.
        git: Perform lint and test only on chaged packs.
        all_packs: Whether to run on all packages.
        verbose: Whether to output a detailed response.
    """

    def __init__(self, dir_packs: str, git: bool, all_packs: bool, verbose: bool):
        global logger
        logger = logging_setup(verbosity=verbose)
        self.config = Configuration()
        self.pkgs: List[str]
        if all_packs or (not dir_packs and git):
            self.pkgs = LintManager.get_all_directories()
            logger.info(f"Packages found {Colors.Fg.cyan}{len(self.pkgs)}{Colors.reset}")
        else:
            self.pkgs = dir_packs.split(',')
        if git:
            self.pkgs = LintManager._get_packages_to_run(self.pkgs)
            for pkg in self.pkgs:
                logger.info(f"Pkgs added after comparing to git {Colors.Fg.cyan}{pkg}{Colors.reset}")
        self.requirements_for_python3: str = get_dev_requirements(3.7, self.config.envs_dirs_base)
        self.requirements_for_python2: str = get_dev_requirements(2.7, self.config.envs_dirs_base)
        self.common_server_created: bool = False

    def run_dev_packages(self, parallel: int, no_flake8: bool, no_bandit: bool, no_mypy: bool, no_pylint: bool,
                         no_test: bool, keep_container: bool, report: str) -> int:
        """Runs the Lint command on all given packages.
        Args:
            parallel: Whether to run command on multiple threads.
            no_flake8: Whether to skip flake8.
            no_bandit: Whether to skip bandit.
            no_mypy: Whether to skip mypy.
            no_pylint: Whether to skip pylint.
            no_test: Whether to skip pytest.
            keep_container: Whether to keep the test container.
            report: directory to create report.
        Returns:
            int. 0 on success and 1 if any package failed
        """
        # Overall tests status
        lint_status: Dict[str, Any] = {
            "status": 0,
            "flake8_exit_code": 0,
            "flake8_errors": {},
            "bandit_exit_code": 0,
            "bandit_errors": {},
            "mypy_exit_code": 0,
            "mypy_errors": {},
            "pylint_exit_code": 0,
            "pylint_errors": {},
            "pytest_exit_code": 0,
            "pytest_errors": {},
            "pytest_collected_tests": []
        }
        # Detailed packages status
        pkgs_status: List[Dict[str, Any]] = []
        # Cumulative exit to be returned
        return_exit_code: int = 0
        # Get docker client for dockr setup
        docker_client = docker.from_env()

        linters: List[Linter] = []
        for pack in self.pkgs:
            logger.debug(f"Permform lint on {Colors.Fg.cyan}{pack}{Colors.reset}")
            linter: Linter = Linter(pack_dir=pack,
                                    req_2=self.requirements_for_python2,
                                    req_3=self.requirements_for_python3)
            linters.append(linter)

        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
            future_to_linter = {}
            pbar = tqdm(unit="pkgs", bar_format='{percentage:3.0f}%:{bar}{r_bar} {desc}', ncols=100,
                        total=len(self.pkgs))
            # Start the load operations
            for linter in linters:
                future_to_linter[executor.submit(fn=linter.run_dev_packages,
                                                 docker_client=docker_client,
                                                 lint_status=lint_status,
                                                 pbar=pbar,
                                                 no_flake8=no_flake8,
                                                 no_bandit=no_bandit,
                                                 no_mypy=no_mypy,
                                                 no_pylint=no_pylint,
                                                 no_test=no_test,
                                                 keep_container=keep_container)] = linter
            for future in concurrent.futures.as_completed(future_to_linter):
                pbar.update()
                pbar.set_description_str(f"{future_to_linter[future].pack_name}")
                exit_code, lint_status, pkg_status = future.result()
                pkgs_status.append(pkg_status)
                if exit_code:
                    return_exit_code = exit_code
            pbar.set_description_str(f"Finished")
            pbar.close()

        # Iterating overall packages required - performing all chosen tests

        self._print_final_results(lint_status)
        if report:
            self._generate_report(pkgs_status, report)

        return return_exit_code

    @staticmethod
    def get_all_directories() -> List[str]:
        """Gets all integration, script and beta_integrations in packages and packs in content repo.

        Returns:
            List. A list of integration, script and beta_integration names.
        """
        all_directories = []
        # get all integrations, scripts and beta_integrations from packs
        for root, _, _ in os.walk(PACKS_DIR):
            if 'Packs/' in root:
                if ('Integrations/' in root or 'Scripts/' in root or 'Beta_Integrations/' in root) \
                        and len(root.split('/')) == 4:
                    logger.debug(f"Add to filter {Colors.Fg.cyan}{root}{Colors.reset}")
                    all_directories.append(root)
        for root, _, _ in os.walk(INTEGRATIONS_DIR):
            if 'Integrations/' in root and len(root.split('/')) == 2:
                logger.debug(f"Add to filter {Colors.Fg.cyan}{root}{Colors.reset}")
                all_directories.append(root)
        for root, _, _ in os.walk(SCRIPTS_DIR):
            if 'Scripts/' in root and len(root.split('/')) == 2:
                logger.debug(f"Add to filter {Colors.Fg.cyan}{root}{Colors.reset}")
                all_directories.append(root)
        for root, _, _ in os.walk(BETA_INTEGRATIONS_DIR):
            if 'Beta_Integrations/' in root and len(root.split('/')) == 2:
                logger.debug(f"Add to filter {Colors.Fg.cyan}{root}{Colors.reset}")
                all_directories.append(root)
        return all_directories

    @staticmethod
    def _get_packages_to_run(pkgs: List[str]) -> List[str]:
        """Checks which packages had changes in them and should run on Lint.

        Returns:
            list[str]. A list of names of packages that should run.
        """
        # get the current branch name.
        current_branch = run_command(f"git rev-parse --abbrev-ref HEAD")
        logger.info(f"Checking for pkgs changed in branch {Colors.Fg.cyan}{current_branch[:-1]}{Colors.reset}")
        pkgs_to_run = []
        pbar = tqdm(iterable=pkgs, unit="pkgs", bar_format='{percentage:3.0f}%:{bar}{r_bar}', ncols=100)
        for directory in pbar:
            if LintManager._check_should_run_pkg(pkg_dir=directory):
                pkgs_to_run.append(directory)
        pbar.close()

        return pkgs_to_run

    @staticmethod
    def _check_should_run_pkg(pkg_dir: str) -> bool:
        """Checks if there is a difference in the package before this Lint run and after it.

        Args:
            pkg_dir: The package directory to check.

        Returns:
            bool. True if there is a difference and False otherwise.
        """
        # get the current branch name.
        current_branch = run_command(f"git rev-parse --abbrev-ref HEAD")

        # This will return a list of all files that changed up until the last commit (not including any changes
        # which were made but not yet committed).
        changes_from_last_commit_vs_master = run_command(f"git diff origin/master...{current_branch}")

        # This will check if any changes were made to the files in the package (pkg_dir) but are yet to be committed.
        changes_since_last_commit = run_command(f"git diff --name-only -- {pkg_dir}")

        # if the package is in the list of changed files or if any files within the package were changed
        # but not yet committed, return True
        if pkg_dir in changes_from_last_commit_vs_master or len(changes_since_last_commit) > 0:
            return True

        # if no changes were made to the package - return False.
        return False

    @staticmethod
    def _print_final_results(lint_status) -> int:
        """Print the results of parallel lint command.

        Args:


        Returns:
            int. 0 on success and 1 if any package failed
     """
        logger.info("\n")
        # Log summary status
        for check in ["flake8", "bandit", "mypy", "pylint", "pytest"]:
            if lint_status[f"{check}_exit_code"]:
                logger.warning(f"{check} - {Colors.Bg.red}[FAILED]{Colors.reset}")
            else:
                logger.warning(f"{check} - {Colors.Bg.green}[PASS]{Colors.reset}")
        logger.info("\n")
        # Log errors from string
        for check in ["flake8", "bandit", "mypy"]:
            if lint_status[f"{check}_exit_code"]:
                logger.info(f"{Colors.underline}{Colors.bold}{check} - Errors summary{Colors.reset}")
                for pkg, error in lint_status[f"{check}_errors"].items():
                    logger.info(f"{Colors.Fg.cyan}Package - {pkg}{Colors.reset}")
                    logger.info(f"{error}")
        # Log errors from list
        for check in ["pylint", "pytest"]:
            if lint_status[f"{check}_exit_code"]:
                logger.info(f"{Colors.underline}{Colors.bold}{check} - Errors summary{Colors.reset}")
                for pkg, errors in lint_status[f"{check}_errors"].items():
                    logger.info(f"{Colors.Fg.cyan}Package - {pkg}{Colors.reset}")
                    for error in errors:
                        logger.info(f"{error}")

    def _generate_report(self, pkgs_status: Dict[str, Any], report: Optional[str]) -> int:
        """Print the results of parallel lint command.

        Args:


        Returns:
            int. 0 on success and 1 if any package failed
        """
        file_loader = FileSystemLoader(f'{self.config.sdk_env_dir}/lint/templates')
        env = Environment(loader=file_loader)
        template = env.get_template('report.jinja2')
        table = template.render(pkgs_status=pkgs_status)
        with open(f"{report}/index{time.strftime('%Y%m%d-%H%M%S')}.html", mode='w') as f:
            f.write(table)
